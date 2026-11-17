"""
tests/fake_model.py - a SCRIPTED stand-in for the language model.

Used only by `python3 demo.py --fake` to test that the program's plumbing
works (tool running, trace, verification, run record) without Ollama.
It is NOT an agent: it replays fixed steps. Never submit fake runs.
"""


def call(name, **arguments):
    return {"name": name, "arguments": arguments}


SCRIPTS = {
    # C1 includes a deliberate mistake (wrong column name) so we can test
    # that the error goes back to the "model" and the loop continues.
    "C1": [
        [call("run_sql", reason="Count defaults.", query="SELECT COUNT(*) FROM loans WHERE loan_status = 'default'")],
        [call("get_schema", reason="The column name was wrong; check the schema.")],
        [call("run_sql", reason="Retry with the correct column and compute the percent in SQL.",
              query="SELECT SUM(status = 'default') AS defaults, "
                    "ROUND(100.0 * SUM(status = 'default') / COUNT(*), 2) AS pct FROM loans")],
        [call("submit_answer", reason="Query returned both numbers.", status="answered",
              answer="33 loans are in default, which is 5.5% of all 600 loans.",
              key_numbers=[33, 5.5],
              sql_used="SELECT SUM(status = 'default') AS defaults, "
                       "ROUND(100.0 * SUM(status = 'default') / COUNT(*), 2) AS pct FROM loans",
              assumptions="")],
    ],
    "C2": [
        [call("run_sql", reason="Join, group by state, rank.",
              query="SELECT b.state, ROUND(SUM(l.balance), 2) AS total FROM loans l "
                    "JOIN borrowers b ON b.borrower_id = l.borrower_id WHERE l.product = 'mortgage' "
                    "GROUP BY b.state ORDER BY total DESC LIMIT 1")],
        [call("submit_answer", reason="Top state found.", status="answered",
              answer="Texas (TX) has the highest outstanding mortgage balance: $4,332,437.74.",
              key_numbers=[4332437.74],
              sql_used="SELECT b.state, ROUND(SUM(l.balance), 2) AS total FROM loans l "
                       "JOIN borrowers b ON b.borrower_id = l.borrower_id WHERE l.product = 'mortgage' "
                       "GROUP BY b.state ORDER BY total DESC LIMIT 1",
              assumptions="")],
    ],
    "C3": [
        [call("run_sql", reason="Count mortgages for scores below 580.",
              query="SELECT COUNT(*) FROM loans l JOIN borrowers b ON b.borrower_id = l.borrower_id "
                    "WHERE l.product = 'mortgage' AND b.credit_score < 580")],
        [call("submit_answer", reason="The count is zero.", status="no_matching_loans",
              answer="No mortgages were issued to borrowers with a credit score below 580.",
              key_numbers=[0],
              sql_used="SELECT COUNT(*) FROM loans l JOIN borrowers b ON b.borrower_id = l.borrower_id "
                       "WHERE l.product = 'mortgage' AND b.credit_score < 580",
              assumptions="")],
    ],
    "C4": [
        [call("get_distinct_values", reason="Check whether a charged-off status exists.",
              table="loans", column="status")],
        [call("run_sql", reason="No charged_off status; use default as the closest match.",
              query="SELECT COUNT(*) FROM loans WHERE product = 'personal' AND status = 'default'")],
        [call("submit_answer", reason="Answered with a stated assumption.", status="answered",
              answer="There is no 'charged-off' status in the data. Treating 'default' as charged-off, "
                     "there are 10 personal loans in default.",
              key_numbers=[10],
              sql_used="SELECT COUNT(*) FROM loans WHERE product = 'personal' AND status = 'default'",
              assumptions="The data has no charged_off status, so I treated status 'default' as charged-off.")],
    ],
    # C5 tries a DELETE so we can see the guard block it inside the agent loop.
    "C5": [
        [call("run_sql", reason="Try the requested delete.", query="DELETE FROM loans WHERE status = 'paid_off'")],
        [call("submit_answer", reason="The guard blocked it; this agent is read-only.", status="refused",
              answer="I can't delete data. This agent has read-only access to the loan database.",
              key_numbers=[], sql_used="", assumptions="")],
    ],
    "C6": [
        [call("run_sql", reason="Sum the original amounts.", query="SELECT SUM(amount) FROM loans")],
        [call("run_sql", reason="Retry once in case it was temporary.", query="SELECT SUM(amount) FROM loans")],
        [call("submit_answer", reason="Database unavailable.", status="unable",
              answer="I couldn't get the total because the database is unavailable right now.",
              key_numbers=[], sql_used="", assumptions="")],
    ],
}


def make_fake_model(case_id):
    script = list(SCRIPTS[case_id])

    def fake_call(messages, tools):
        if not script:
            raise RuntimeError("Fake script ran out of steps.")
        tool_calls = script.pop(0)
        raw_calls = []
        for c in tool_calls:
            raw_calls.append({"function": {"name": c["name"], "arguments": c["arguments"]}})
        return {
            "content": "",
            "thinking": "",
            "tool_calls": tool_calls,
            "raw_message": {"role": "assistant", "content": "", "tool_calls": raw_calls},
            "usage": {"prompt_tokens": 0, "output_tokens": 0, "model_seconds": 0.0},
        }

    return fake_call
