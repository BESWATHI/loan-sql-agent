# Demo plan (about 6 minutes)

1. **(30s) What it is.** One sentence on the task, show the tools table in README.
2. **(1.5 min) C1 or C2 live.** `python3 demo.py --case C2`. Point at each step:
   the model's choice, its reason, the tool result, the next decision.
3. **(1 min) C3.** Zero result reported honestly, backed by re-running the SQL.
4. **(1.5 min) C4.** The agent checks which statuses exist and does not just trust the
   question. Point to the stated assumption (or the clarification request).
5. **(1 min) C5 and C6.** Refusal with the database hash unchanged; the outage reported
   with no invented numbers.
6. **(30s) Verification.** Show the PASS/FAIL checks. Run `python3 -m tests.test_verifier`
   to show the checker catches false answers.
7. **(30s each) Contributions.** Each person explains their own part.

**Backup:** a local model can be slow or inconsistent. Have a recent real
`RUN_RECORD.md` open in case the live run misbehaves, and if it fails live, explain the
failure. The rubric rewards showing what really happened.

## Questions to be ready for

- How does the model choose a tool? What does Python do vs. the model?
- What stops the agent from deleting data, even if the model tries?
- How do you know an answer is right without trusting the model?
- What happens when a query has an error?
- Why did you pick C4? What would a bad agent do there?
- What happens if the model never calls submit_answer?
