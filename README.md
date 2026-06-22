# MatchEngine 
Welcome to the documentation for the matchengine! The Matchengine is a system designed to match cancer patients to genomically driven clinical trials using Clinical Trial Markup Language (CTML) and patient clinical and genomic data. It utilizes the the MatchminerAPI and MatchminerUI for displaying trial match information.


The matchengine can be used on local instances that provide access to private data. If you are interested in the development of new features, or in setting up a local instance of the MatchMiner system, please see the documentation, or contact [matchminer@dfci.harvard.edu](https://app.gitbook.com/@matchminer/s/matchminer)

# Documentation
[Gitbook documentation](https://matchminer.gitbook.io/matchminer/matchengine-v2/introduction)

# Running Tests

## Prerequisites

- MongoDB running locally
- `SECRETS_JSON.json` at the repo root with your connection details (see `SECRETS_JSON.json` for format)
- Python virtual environment set up at `.venv/`

If `pytest` is not yet installed in the venv:
```bash
.venv/bin/python -c "import ensurepip; ensurepip.bootstrap()"
.venv/bin/python -m pip install pytest
```

## Integration Tests

Runs the full matching engine against pre-loaded test data in the `integration` MongoDB database. Requires the `integration` db to be populated (BSON files at `matchengine/tests/data/integration_data/`).

> Make sure `MONGO_DBNAME` in your `SECRETS_JSON.json` is set to `integration`.

```bash
SECRETS_JSON=SECRETS_JSON.json .venv/bin/python -m pytest matchengine/tests/test_matchengine_integration.py -v
```

Run a single test:
```bash
SECRETS_JSON=SECRETS_JSON.json .venv/bin/python -m pytest matchengine/tests/test_matchengine_integration.py::IntegrationTestMatchengine::test_tmb -v
```

## Demo Tests

Loads two realistic patients into a `demo` MongoDB database and runs the matching engine against a FLAURA-style trial (NCT02477839) with three arms to demonstrate the engine's precision:

- **MRN 1035** — EGFR p.E746_A750del (In_Frame_Del, 5 genomic docs including EXA p.L211M which has no trial match)
- **MRN 1036** — EGFR p.L858G (Missense, 1 genomic doc)
- **ARM A**: EGFR + In_Frame_Del → MRN 1035 only
- **ARM B**: EGFR + any Mutation → both patients
- **ARM C**: EGFR + exact p.L858R → neither patient (demonstrates exclusion precision)

The database is created fresh on each run — no prior setup required.

Mock data lives in `matchengine/tests/data/mock/`.

```bash
SECRETS_JSON=SECRETS_JSON.json .venv/bin/python -m pytest matchengine/tests/test_matchengine_demo.py -v
```

## Run All Tests

```bash
SECRETS_JSON=SECRETS_JSON.json .venv/bin/python -m pytest matchengine/tests/ -v
```

# Dev

To run new patient data and trials, do the following:

1. Place the data in the appropriate folder to match the data version: for example, v1_data/ (root level)
   1. The data for clinical, genomic, and trial should be split into the v1_data/clinical, v1_data/trials, and v1_data/genomic folders
2. Run the matching!
   1. SECRETS=SECRETS_JSON.json .venv/bin/python -m matchengine.main load -t v1_data/trials/ -c v1_data/clinical/ -g v1_data/genomic --trial-form json --patient-format json --db v1

Important:
- This data gets stored in the mongodb database under the **database named v1** (see the *--db v1* option which overrode where to store the results)
- Use MongoDB Compass to look at the results

## Creating a clinical trial report

Once the matching data is in the Mongo database, you can simply export the full trial_match collection as JSON. Ensure you also export the clinical and genomic collections as well. There are 3 pieces of custom for each report that will be needed per patient:

1. trial_match data - query for the specific patient
2. clinical - query for the specific patient
3. genomic - query for the specific patient

The ctm-report-preview repo has functionality that will ingest those 3 files and create a nice PDF report for you :-)

