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
- Reviewed and merged Sachin's pull request (#1), then ran the final 8-case run on the merged code (8 of 8 passed, `run_20261124_104839`)
- Wrote the problem statement; prepared the workflow diagram, slides and project PDF with an AI assistant
- Set up Git and the GitHub repository
- Wrote REPORT.md Sections 1, 2, 5, 7 and Section 4 for C1, C2, and C4

**Something I can explain in detail:** why `run_sql` refuses a filter like `'charged-off'` instead of returning 0, and how we got there through the failed runs.

## Sachin Muttu Baraddi (GitHub: SachinBaraddi)

**Main responsibility:** data and evaluation; new test cases and checking the results

- Set up the project on a second laptop using only the README; all tests and the demo passed (6 of 6, `run_20261117_192550`), showing the project runs on another machine
- Fixed the README: outdated test counts, when `ollama serve` is needed on Mac, `make_data.py` marked optional, and C7/C8 added to the test cases table
- Added two new test cases: C7 (date filter, average auto loan rate in 2023) and C8 (ranking, product with the highest default rate)
- Wrote the hand-checked answers for C7 and C8 in `expected_values.py` using plain Python on the CSV files, including a tie check for C8, and added both cases to `cases.py` with "why_chosen" lines and the default-rate definition
- Ran C7 and C8 three times each (3 of 3 passed for both)
- Fixed a bug in `db_tools.py` where the same invalid value used twice repeated the warning, and added 2 tests to `tests/test_tools.py` (26 of 26 passed)
- Code changes (C7/C8 functions, bug fix, new tests) were developed with an AI assistant; I ran them, checked the results against the data, and committed them
- Read and can explain `make_data.py`, `expected_values.py`, `cases.py` and `verify.py`
- Wrote REPORT.md Section 3, Section 4 for C3, C5, C6, C7 and C8, and Section 6, including three limitations of the verifier

**Something I can explain in detail:** why C8 checks the default rate 7.85 and not just the name "auto", since auto also has the most defaults, so the name alone wouldn't prove the agent computed a rate.


## Done together

- Reviewing each other's work through pull requests: Swathi reviewed and merged Sachin's pull request (#1); Sachin reviewed and merged Swathi's pull request (swathi-docs)
- Checking that the project runs on both laptops (6 of 6 on each), and the final 8-case run on the merged code (8 of 8)
- REPORT.md: each member wrote the sections listed above
- Preparing and presenting the demo together
