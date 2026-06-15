import os
from argparse import Namespace
from unittest import TestCase

from matchengine.internals.database_connectivity.mongo_connection import MongoDBConnection
from matchengine.internals.engine import MatchEngine
from matchengine.internals.load import load_clinical, load_genomic, load_trials_json
from matchengine.tests.timetravel_and_override import set_static_date_time

MOCK_DIR = os.path.join('matchengine', 'tests', 'data', 'mock')
CLINICAL_DIR = os.path.join(MOCK_DIR, 'clinical_json')
GENOMIC_DIR = os.path.join(MOCK_DIR, 'genomic_json')
TRIALS_DIR = os.path.join(MOCK_DIR, 'trials')
TRIAL_FILE = os.path.join(TRIALS_DIR, 'nct_egfr_nsclc_stub.json')


class StagingTestMatchengine(TestCase):
    """
    End-to-end demo test using realistic mock data.

    Two patients:
      - MRN 1035 (EGFR p.E746_A750del, In_Frame_Del, NSCLC) — 5 genomic docs
      - MRN 1036 (EGFR p.L858G, Missense_Mutation, NSCLC) — 1 genomic doc

    One FLAURA-style trial (NCT02477839) with three arms:
      - ARM A (id=1): EGFR + In_Frame_Del   -> MRN 1035 matches, 1036 does NOT
      - ARM B (id=2): EGFR + any Mutation   -> both patients match
      - ARM C (id=3): EGFR + p.L858R exact  -> neither patient matches (precision demo)

    EXA p.L211M on MRN 1035 is stored in the genomic collection but generates no trial
    matches because no arm criteria references EXA.

    Expected match doc counts (report_all_clinical_reasons=True -> 3 docs per AND block per level):
      MRN 1035: step(3) + ARM A(3) + ARM B(3) = 9
      MRN 1036: step(3) + ARM B(3)             = 6
      Total: 15
    """

    def setUp(self):
        set_static_date_time()

        args = Namespace(
            clinical=CLINICAL_DIR,
            genomic=GENOMIC_DIR,
            trial=TRIAL_FILE,
            patient_format='json',
            trial_format='json',
            db_name='demo',
        )

        with MongoDBConnection(read_only=False, db='demo', async_init=False) as db:
            db.clinical.drop()
            db.genomic.drop()
            db.trial.drop()
            db.trial_match.drop()

            load_clinical(db, args)

        # genomic load needs both rw and ro connections (map_clinical_to_genomic reads ro)
        with MongoDBConnection(read_only=False, db='demo', async_init=False) as db_rw, \
             MongoDBConnection(read_only=True,  db='demo', async_init=False) as db_ro:
            load_genomic(db_rw, db_ro, args)

        with MongoDBConnection(read_only=False, db='demo', async_init=False) as db:
            load_trials_json(args, db)

        self.me = MatchEngine(
            db_name='demo',
            config='matchengine/config/dfci_config.json',
            plugin_dir='matchengine/plugins/',
            match_document_creator_class='DFCITrialMatchDocumentCreator',
            match_on_deceased=False,
            match_on_closed=False,
            num_workers=1,
            report_all_clinical_reasons=True,
            ignore_run_log=True,
        )

    def tearDown(self):
        if hasattr(self, 'me'):
            self.me.__exit__(None, None, None)

    def test_staging_data_loaded(self):
        """Verify all mock documents were loaded and linked correctly."""
        with MongoDBConnection(read_only=True, db='demo', async_init=False) as db:
            self.assertEqual(db.clinical.count_documents({}), 2)
            self.assertEqual(db.genomic.count_documents({}), 6)
            self.assertEqual(db.trial.count_documents({}), 1)

            # MRN 1035: 5 genomic docs (EGFR ex19del, TP53, KRAS, STK11, EXA L211M)
            clinical_1035 = db.clinical.find_one({'SAMPLE_ID': '5d2799d86756630d8dd065b8'})
            self.assertIsNotNone(clinical_1035)
            linked_1035 = db.genomic.count_documents({'CLINICAL_ID': clinical_1035['_id']})
            self.assertEqual(linked_1035, 5)

            # MRN 1036: 1 genomic doc (EGFR L858G)
            clinical_1036 = db.clinical.find_one({'SAMPLE_ID': '5d2799d86756630d8dd065b9'})
            self.assertIsNotNone(clinical_1036)
            linked_1036 = db.genomic.count_documents({'CLINICAL_ID': clinical_1036['_id']})
            self.assertEqual(linked_1036, 1)

            # EXA p.L211M is present in genomic for MRN 1035
            exa_doc = db.genomic.find_one({'TRUE_HUGO_SYMBOL': 'EXA', 'TRUE_PROTEIN_CHANGE': 'p.L211M'})
            self.assertIsNotNone(exa_doc)
            self.assertEqual(exa_doc['CLINICAL_ID'], clinical_1035['_id'])

    def test_egfr_nsclc_trial_match(self):
        """
        Demonstrate the precision matching engine:
          - MRN 1035 (In_Frame_Del) matches ARM A and ARM B
          - MRN 1036 (L858G Missense) matches ARM B only — not ARM A (wrong classification)
          - ARM C (exact p.L858R) matches neither patient
          - EXA p.L211M on MRN 1035 generates no matches
        """
        self.me.get_matches_for_all_trials()

        matches = self.me._matches.get('NCT02477839', {})
        self.assertGreater(len(matches), 0, 'Expected at least one match for NCT02477839')

        all_match_docs = [doc for docs in matches.values() for doc in docs]

        # MRN 1035: step(3) + ARM A(3) + ARM B(3) = 9; MRN 1036: step(3) + ARM B(3) = 6
        self.assertEqual(len(all_match_docs), 15)

        # ARM C (exact p.L858R) has no matches — neither patient has L858R
        arm_c_matches = [d for d in all_match_docs if d.get('internal_id') == 3]
        self.assertEqual(len(arm_c_matches), 0, 'ARM C (p.L858R exact) should match no patient')

        # EXA p.L211M generates no trial matches (no arm references EXA)
        exa_matches = [d for d in all_match_docs if d.get('true_hugo_symbol') == 'EXA']
        self.assertEqual(len(exa_matches), 0, 'EXA gene should generate no trial matches')

        # MRN 1035: arm-level gene matches for ARM A (In_Frame_Del) and ARM B (any Mutation)
        p1035_arm_gene = [
            d for d in all_match_docs
            if d.get('mrn') == '1035' and d.get('match_type') == 'gene' and d.get('match_level') == 'arm'
        ]
        self.assertEqual(len(p1035_arm_gene), 2, 'MRN 1035 should have gene matches for ARM A and ARM B')
        self.assertEqual(
            {d['internal_id'] for d in p1035_arm_gene}, {1, 2},
            'MRN 1035 should match ARM A (id=1) and ARM B (id=2)',
        )
        for doc in p1035_arm_gene:
            self.assertEqual(doc['genomic_alteration'], 'EGFR p.E746_A750del')
            self.assertEqual(doc['cancer_type_match'], 'specific')
            self.assertEqual(doc['vital_status'], 'alive')
            self.assertTrue(doc['show_in_ui'])

        # MRN 1036: arm-level matches only for ARM B — L858G is Missense, not In_Frame_Del, not p.L858R
        p1036_arm_docs = [
            d for d in all_match_docs
            if d.get('mrn') == '1036' and d.get('match_level') == 'arm'
        ]
        self.assertGreater(len(p1036_arm_docs), 0, 'MRN 1036 should have arm-level matches')
        self.assertEqual(
            {d['internal_id'] for d in p1036_arm_docs}, {2},
            'MRN 1036 should only match ARM B (id=2)',
        )

        # Confirm MRN 1036 ARM B gene match carries the L858G alteration
        p1036_gene = [d for d in p1036_arm_docs if d.get('match_type') == 'gene']
        self.assertEqual(len(p1036_gene), 1)
        self.assertEqual(p1036_gene[0]['genomic_alteration'], 'EGFR p.L858G')

    def test_staging_trial_match_written_to_db(self):
        """After update_matches, trial_match collection has all 15 expected docs."""
        self.me.get_matches_for_all_trials()
        for protocol_no in self.me.trials.keys():
            self.me.update_matches_for_protocol_number(protocol_no)

        with MongoDBConnection(read_only=True, db='demo', async_init=False) as db:
            count = db.trial_match.count_documents({'protocol_no': 'NCT02477839'})
            self.assertEqual(count, 15)

            # ARM A gene match for MRN 1035 (EGFR In_Frame_Del)
            arm_a_1035 = db.trial_match.find_one({
                'protocol_no': 'NCT02477839',
                'internal_id': 1,
                'match_level': 'arm',
                'match_type': 'gene',
                'mrn': '1035',
            })
            self.assertIsNotNone(arm_a_1035)
            self.assertEqual(arm_a_1035['code'], 'ARM A')
            self.assertEqual(arm_a_1035['genomic_alteration'], 'EGFR p.E746_A750del')
            self.assertEqual(arm_a_1035['true_variant_classification'], 'In_Frame_Del')
            self.assertEqual(arm_a_1035['oncotree_primary_diagnosis_name'], 'Non-Small Cell Lung Cancer')
            self.assertTrue(arm_a_1035['show_in_ui'])

            # ARM C has zero matches (neither patient has p.L858R)
            arm_c_count = db.trial_match.count_documents({
                'protocol_no': 'NCT02477839',
                'internal_id': 3,
            })
            self.assertEqual(arm_c_count, 0, 'ARM C (p.L858R exact) should have no matches in DB')

            # MRN 1036 is only in ARM B at arm level
            p1036_arm_ids = {
                doc['internal_id']
                for doc in db.trial_match.find({
                    'protocol_no': 'NCT02477839',
                    'mrn': '1036',
                    'match_level': 'arm',
                })
            }
            self.assertEqual(p1036_arm_ids, {2}, 'MRN 1036 should only appear in ARM B at arm level')
