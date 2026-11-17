# Individual contributions

> Fill this in together and keep it honest. The rubric grades each person on
> explaining their OWN work. Commit history should match what is written here.

## Swathi Baba Eswarappa (GitHub: BESWATHI)

**Main responsibility:** agent loop and safety; running and debugging the agent

- Set up Ollama with qwen3:8b and ran all the tests and real demo runs on my laptop
- Agent and safety code (`agent.py`, `tools.py`, `db_tools.py`, `model_client.py`, `tests/test_tools.py`): developed with an AI assistant; I tested it, reviewed the results, and decided which changes to make
- Found and analyzed failures in real runs: the C1 evidence problem, C2 passing partly by luck, the C4 failures, and the C1 regression
- Tested the C4 fixes step by step (warning, thinking mode, tool refusal) and re-ran all cases after each change
- Ran the reliability check (18 of 18 passed)
- Set up Git and the GitHub repository
- Wrote REPORT.md Sections 1, 2, 5, 7 and Section 4 for C1, C2, and C4

**Something I can explain in detail:** why `run_sql` refuses a filter like `'charged-off'` instead of returning 0, and how we got there through the failed runs.

## Sachin Muttu Baraddi (GitHub: SachinBaraddi)

**Main responsibility:** data and evaluation

- `make_data.py`:
- `expected_values.py`:
- `cases.py`:
- `verify.py`:
- `demo.py` / run record:
- `tests/test_verifier.py`:

**Something I can explain in detail:** (e.g. how the verifier re-runs the agent's SQL)

## Done together

- Choosing the six test cases and why
- Running the demo and reviewing the run records
- Writing REPORT.md
- Reviewing each other's code
