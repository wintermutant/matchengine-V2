"""
Export all trial_match, clinical, and genomic documents for a patient.

Usage:
    SECRETS_JSON=SECRETS_JSON.json python export_matches.py --patient 7439568 --output export/

Arguments:
    --patient   SAMPLE_ID of the patient to export (repeatable for multiple patients)
    --output    Directory to write output files (one JSON per patient)
    --db        MongoDB database name (default: v1)
"""

import argparse
import json
import os

import pymongo
from bson import json_util


def get_db(db_name: str):
    secrets_path = os.environ.get("SECRETS_JSON")
    if not secrets_path:
        raise RuntimeError("SECRETS_JSON environment variable not set")
    with open(secrets_path) as f:
        secrets = json.load(f)
    client = pymongo.MongoClient(
        host=secrets.get("MONGO_HOST", "localhost"),
        port=int(secrets.get("MONGO_PORT", 27017)),
    )
    return client[db_name]


def export_patient(db, sample_id: str, output_dir: str):
    clinical = db.clinical.find_one({"SAMPLE_ID": sample_id})
    if not clinical:
        print(f"  WARNING: no clinical record found for SAMPLE_ID={sample_id}")

    genomic = list(db.genomic.find({"SAMPLE_ID": sample_id}))
    trial_matches = list(db.trial_match.find({"sample_id": sample_id}))

    payload = {
        "clinical": clinical,
        "genomic": genomic,
        "trial_match": trial_matches,
    }

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"{sample_id}.json")
    with open(out_path, "w") as f:
        f.write(json_util.dumps(payload, indent=2))

    print(f"  {sample_id}: {len(trial_matches)} matches, {len(genomic)} genomic docs → {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Export match data for one or more patients.")
    parser.add_argument("--patient", dest="patients", action="append", required=True,
                        metavar="SAMPLE_ID", help="SAMPLE_ID to export (repeatable)")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--db", default="v1", help="MongoDB database name (default: v1)")
    args = parser.parse_args()

    db = get_db(args.db)
    print(f"Exporting from db={args.db!r} → {args.output}/")
    for sample_id in args.patients:
        export_patient(db, sample_id, args.output)


if __name__ == "__main__":
    main()
