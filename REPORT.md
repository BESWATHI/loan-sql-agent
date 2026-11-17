# Mini-project report: Loan Portfolio SQL Agent

**Course:** CSYE 7374 Agentic AI
**Team:** Swathi Baba Eswarappa, Sachin Muttu Baraddi
**Model:** qwen3:8b via Ollama (local), temperature 0, thinking off
**Main evidence:**
- `runs/run_20261116_203132/RUN_RECORD.md`: final full run, 6 of 6 passed
- `runs/run_20261116_203541/RUN_RECORD.md`: reliability check, 18 of 18 passed

**Repository:** https://github.com/BESWATHI/loan-sql-agent
**Commit:** (add the final commit hash before submitting: `git log -1 --format=%h`)

## Section 1: What the Agent Does

Our project is a loan portfolio analysis agent that uses an AI model to answer questions about loan data stored in a database. For example, if someone asks, "How many loans are in default?", the agent checks the database, runs SQL queries, and returns an answer based on the actual data instead of guessing.

We used the **qwen3:8b model running locally through Ollama**, with temperature set to 0. The database contains 300 borrowers and 600 loans generated using synthetic data. The model has four tools available: `get_schema`, `get_distinct_values`, `run_sql`, and `submit_answer`.

The model decides which tool to use and what to do next based on the results it receives. Python checks and executes those tool calls but does not decide their order. We also restricted the agent to read-only database operations so it cannot change or delete any records.

## Section 2: How the Agent Makes Decisions

One example that helped us understand the agent's decision-making was test case C4. In this test, we asked the agent about charged-off personal loans, even though `charged-off` is not a valid loan status in our database.

In our earlier runs, the agent first checked the available loan statuses and saw that `charged-off` was not one of them. However, it still went ahead and queried the database using that status. Since there were no matching records, it returned zero. The problem was that it treated an invalid status as if it were a valid status with no matching loans.

We tried adding a warning to the tool response, but the model ignored it. We also tested thinking mode, which made the model more careful but did not fix the problem.

We then changed the SQL tool so that it **refuses queries that filter on values that don't exist in the data, such as an invalid status**. This applies to `status`, `product`, and `state` values.

In the final run (`run_20261116_203132`), we could see the agent change its approach based on the tool response.

At **Step 4**, the agent tried to query loans with the status `charged-off`. The tool rejected the query and returned the valid statuses.

At **Step 5**, the agent changed its approach. Its reason for the next tool call was:

"To calculate the number of default personal loans, since 'charged-off' is not a valid status."

Instead of repeating the invalid query, it used `default` to find the number of personal loans in that category.

At **Step 6**, it submitted the answer as 10 loans and clearly stated that it was treating `charged-off` as `default` for this question.

In another successful run (`run_20261116_202524`), the agent asked for clarification instead of making an assumption. Both outcomes were acceptable because the agent recognized that the requested status did not exist.

This example shows how the agent makes decisions based on what the tools return. It did not simply follow a fixed set of SQL queries. When the tool refused an invalid query, the model used that information to choose a different action.

The final tests were completed with thinking mode turned off, which also showed us that enforcing the rule in the tool was enough to fix this issue without requiring additional model reasoning.

## Section 3: Results

> **Sachin:** results table for all cases (runs, passed, notes), from `run_20261116_203541`.

## Section 4: Each Case

### C1: Default count and rate
We chose this case because counting defaulted loans and calculating their percentage is a basic risk question that could come up in a monthly loan portfolio report. It also helped us check whether the agent could calculate both numbers correctly using one table. In the final run (run_20261116_203132), the agent used one SQL query with SUM(status = 'default') and returned 33 defaulted loans out of 600, with a default rate of 5.5%. The answer was justified because all three numbers came directly from the query, matched our independently calculated values, and were confirmed when the verifier ran the SQL again.

### C2: State with the highest outstanding mortgage balance
We chose this case because it requires combining information from two tables, making it more challenging than C1. In the final run, the agent initially tried to access loans.state, which caused a no such column error because state information is stored in the borrowers table. The agent used the error to correct its query, taking state from the borrowers table instead, and found that Texas (TX) had the highest total mortgage balance at $4,332,437.74. The final answer was justified because it came directly from the corrected query, matched our hand-checked result, and did not include any unnecessary filters.

### C3: No matching loans
> **Sachin**

### C4: Status that does not exist
We chose this case to test whether the agent could recognize a loan status that does not exist in the database instead of incorrectly treating it as zero matching loans. As explained in Section 2, the agent initially tried to query charged-off, but the tool rejected it and showed the valid statuses. In the final run, the agent used default instead and returned 10 personal loans, clearly stating that this was an assumption. We considered the answer justified because the tool provided the valid statuses, the query supported the count of 10, and the agent was transparent about how it interpreted the question.

### C5: Invalid request (delete)
> **Sachin**

### C6: Tool failure (database outage)
> **Sachin**

## Section 5: Failures and What We Changed

During the first C1 test, the agent correctly returned 33 defaulted loans out of 600, giving a default rate of 5.5%. However, there were two problems with how it reported the answer. It included 33 and 600 in `key_numbers` but left out the calculated percentage of 5.5. It also listed a SQL query in `sql_used` that it had never actually executed.

The numbers themselves were supported by the real tool results, but the reported evidence was incomplete and inaccurate. We also realized that our verifier had a problem because it only checked the SQL listed in `sql_used` rather than considering all the queries the agent had actually executed.

We corrected both the agent instructions and the verifier so that the reported calculations and SQL evidence could be checked more accurately.

In an early C2 run, the agent added an unnecessary filter, `status = 'current'`, even though the question did not ask for it. The answer still came out as Texas (TX) because there were no late or defaulted mortgages in Texas, but the second-place state would have been different. We added an instruction not to introduce filters that the user did not request, and the final runs no longer showed this behavior.

Another failure happened in C4, where the model ignored its own observation that `charged-off` was not a valid status. Adding warnings and enabling thinking mode did not solve the issue. The successful fix was making the SQL tool reject filters containing values that do not exist in the database.

We also found a regression in C1 after changing a prompt example. The agent counted all 600 loans as defaulted instead of counting only the 33 loans with default status. Our verifier caught the incorrect answer, and we fixed the example before rerunning the complete test suite.

The run folders from our early experiments were accidentally deleted, so the results of the first C1 failure, the early C2 run, and the earlier C4 experiments are supported by our saved terminal output. The later runs are available in the `runs/` folder, along with the project's Git history.

After the fixes, all six test cases passed. We repeated the six cases three times and obtained **18 successful runs out of 18**.

## Section 6: How We Checked the Answers

> **Sachin:** explain `verify.py` in plain words: why our checks do not depend on the model's own claims.

## Section 7: Limitations and What We Learned

One limitation is that we tested the agent using six predefined cases and a synthetic database. Although all 18 final runs passed, this does not mean the agent will handle every possible question correctly. Also, because the model was running at temperature 0, the repeated runs produced identical results. This shows consistency under the tested conditions, but not necessarily robustness to different model behavior.

The biggest thing I learned from this project is that building an AI agent is not just about getting a model to call tools. We also need to make sure those tools are safe and that the answers can actually be verified.

I also realized that getting the right answer does not always mean the agent followed the correct process. In C1, the answer was correct, but the reported SQL evidence was wrong. We even found that our own verifier needed improvement, which showed us why we should not assume the checking process is always correct either.

The C4 experiments were another important lesson. The model had already seen that the status was invalid but still queried it. We learned that giving instructions or warnings is not always enough, and that some rules are better enforced directly through the tools.

For me, the most useful part of the project was understanding why the failures happened, testing different fixes, and seeing how those changes affected the final results.

*AI assistance disclosure: The code was developed with assistance from an AI assistant. We tested and debugged the implementation using actual runs, reviewed the results, and wrote the explanations based on our understanding of the project.*
