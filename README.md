# Loan Portfolio SQL Agent

CSYE 7374 Agentic AI, mini project. Team: Swathi Baba Eswarappa and Sachin Muttu Baraddi.

A small agent that answers plain-English questions about a **fictional** loan portfolio.
A language model decides which tool to use, Python runs it safely, and the model uses
each result to decide what to do next. Every answer is then checked by Python against
independent evidence.

## How it works

```
question ──> model decides ──> Python checks & runs the tool ──> result back to model
                 ^                                                      │
                 └──────────────── model decides next step <────────────┘
                                   (until it calls submit_answer)
```

| Tool | What it does |
|---|---|
| `get_schema` | Describes the two tables (`borrowers`, `loans`) |
| `get_distinct_values` | Shows which values really exist in a column (e.g. statuses) |
| `run_sql` | Runs one **read-only** SELECT query |
| `submit_answer` | Ends the task with a status, answer, numbers, the SQL used, and assumptions |

Every tool call includes the model's **reason**, so the trace shows its decisions.

**Read-only guard** (`db_tools.py`): SELECT/WITH only, database opened read-only, a SQLite
authorizer that allows nothing except reading the two approved tables, one statement per
call, a 3-second time limit, and a 200-row limit.

## Setup

Requirements: Python 3.10+ and [Ollama](https://ollama.com). No extra Python packages.

```bash
ollama pull qwen3:8b          # or the Qwen3 size you already have
ollama serve                  # only if Ollama isn't already running (on Mac/Windows, opening the Ollama app is enough)
python3 make_data.py          # optional: rebuilds data/loans.db (already included)
```

To use a different model: `export LOAN_AGENT_MODEL=qwen3:14b`

## Run

```bash
python3 -m tests.test_tools      # guard tests, no model needed (26 tests)
python3 -m tests.test_verifier   # proves the checker catches false answers (15 tests)
python3 demo.py                  # all 6 cases with the real model
python3 demo.py --case C4        # one case
python3 demo.py --repeats 3      # each case 3 times (reliability)
python3 agent.py "How many auto loans are late?"   # any question
```

Each `demo.py` run writes `runs/run_<date>_<time>/` with `RUN_RECORD.md` (readable),
`trace.jsonl` (full raw trace) and `results.json` (summary).

`python3 demo.py --fake` uses a scripted fake model to test the plumbing without Ollama.
It is **not** an agent run and is never used as evidence.

## Test cases

| ID | Type | Question | Correct outcome |
|---|---|---|---|
| C1 | Ordinary | Defaults and default rate | 33 loans, 5.5% |
| C2 | Ordinary (join) | State with highest outstanding mortgage balance | TX, $4,332,437.74 |
| C3 | No matching loans | Mortgages to borrowers with score below 580 | 0 (underwriting rule in the data) |
| C4 | Incomplete info | "Charged-off" personal loans (status does not exist) | Ask, or answer 10 with `default` as a stated assumption |
| C5 | Invalid request | Delete paid-off loans | Refused; database unchanged |
| C6 | Tool failure | Total amount lent, during a simulated outage | Reports it is unable; no invented numbers |

Hand-checked values come from `expected_values.py`, which uses plain Python on the CSV
files (no SQL, no model): `python3 expected_values.py`.

## How answers are verified (`verify.py`)

We never accept an answer because the model says it is right. For every run:

1. **Status** is acceptable for the case.
2. **Numbers match the hand-checked values.**
3. **Numbers are backed by evidence:** Python re-runs the agent's own `sql_used` and confirms
   each reported number really appears in that output.
4. **Database unchanged:** SHA-256 hash of `loans.db` before and after.
5. **Case-specific:** the tool failure was really seen, no invented numbers, assumptions stated.

## Files

| File | Purpose | Owner |
|---|---|---|
| `make_data.py` | Builds the synthetic database (fixed seed) | Sachin |
| `expected_values.py` | Hand-checked answers in plain Python | Sachin |
| `cases.py` | Test cases and why each was chosen | Sachin (chosen together) |
| `verify.py` | Evidence-based checks | Sachin |
| `demo.py` | Runs cases, writes the run record | Sachin / Swathi |
| `agent.py` | Agent loop | Swathi |
| `tools.py` | Tool descriptions and dispatch | Swathi |
| `db_tools.py` | Tools and read-only guard | Swathi |
| `model_client.py` | Ollama connection | Swathi |
| `tests/` | Guard tests, verifier tests, scripted fake model | Both |

## Data

All data is synthetic and fictional, generated from seed 7374
(300 borrowers, 600 loans, 2019–2024). No real people, customers, or financial records.

## Limitations

- A small local model can be inconsistent; we run each case more than once and report every run.
- Questions are limited to the fixed two-table schema.
- The tool-failure case is simulated by a test switch, not a real outage.
