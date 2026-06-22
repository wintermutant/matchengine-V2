"""
Split a combined clinical+genomic JSON file into the per-record files that
matchengine's `load` command expects.

Usage:
    python split.py [path/to/input.json]

Defaults to version1.json in the project root if no path is given.
Output lands in clinical/ and genomic/ next to this script.
"""

import json
import os
import sys

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))


def split(source_path: str):
    with open(source_path) as f:
        data = json.load(f)

    clinical_dir = os.path.join(HERE, "clinical")
    genomic_dir = os.path.join(HERE, "genomic")
    os.makedirs(clinical_dir, exist_ok=True)
    os.makedirs(genomic_dir, exist_ok=True)

    for rec in data["clinical"]:
        rec["VITAL_STATUS"] = rec.get("VITAL_STATUS", "").lower()
        sid = rec["SAMPLE_ID"]
        with open(os.path.join(clinical_dir, f"{sid}.json"), "w") as f:
            json.dump(rec, f, indent=2)

    for i, rec in enumerate(data["genomic"]):
        sid = rec["SAMPLE_ID"]
        with open(os.path.join(genomic_dir, f"{sid}_{i}.json"), "w") as f:
            json.dump(rec, f, indent=2)

    print(f"Wrote {len(data['clinical'])} clinical, {len(data['genomic'])} genomic files to {HERE}")


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "version1.json")
    split(source)
