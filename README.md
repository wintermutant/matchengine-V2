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
