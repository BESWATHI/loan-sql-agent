"""
demo.py - runs the demonstration cases and writes the run record.

Owner: Sachin (evaluation and report), with Swathi

Usage:
    python3 demo.py                 # all 6 cases with the real model
    python3 demo.py --case C2       # one case
    python3 demo.py --repeats 3     # run each case 3 times (reliability check)
    python3 demo.py --fake          # offline plumbing test with a SCRIPTED model
                                    # (not a real agent run - never submit these)

Output folder: runs/run_<date>_<time>/
    RUN_RECORD.md   readable record: every decision, tool call, result, check
    trace.jsonl     the complete raw trace, one line per run
    results.json    pass/fail summary
"""

import argparse
import datetime
import json
import os

import agent
import cases
import db_tools
import verify

HERE = os.path.dirname(os.path.abspath(__file__))


def short(value, limit=160):
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    text = text.replace("|", "\\|").replace("\n", " ")
    if len(text) > limit:
        return text[:limit] + "..."
    return text


def result_summary(result):
    if not result.get("ok"):
        return "ERROR: " + result.get("error", "")
    if "rows" in result:
        text = "%d row(s): %s" % (result["row_count"], json.dumps(result["rows"], default=str))
        if result.get("warnings"):
            text = text + " WARNING: " + " ".join(result["warnings"])
        return text
    if "values" in result:
        parts = []
        for item in result["values"]:
            parts.append("%s (%s)" % (item["value"], item["count"]))
        return "values: " + ", ".join(parts)
    return "schema returned"


def write_record(path, run_info, runs):
    lines = []
    lines.append("# Run record: Loan Portfolio SQL Agent")
    lines.append("")
    lines.append("- **Date:** %s" % run_info["date"])
    lines.append("- **Model:** %s" % run_info["model"])
    lines.append("- **Database:** synthetic SQLite, 300 borrowers, 600 loans (seed 7374)")
    if run_info["fake"]:
        lines.append("")
        lines.append("> **WARNING: SCRIPTED FAKE MODEL.** This run only tests the program's plumbing. "
                     "It is not evidence of agent behavior and must not be submitted.")
    lines.append("")
    lines.append("All runs are kept in this record, including failed ones.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Case | Run | What it tests | Final status | Result | Tool calls | Tokens (in/out) | Time (s) |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for run in runs:
        final = run["outcome"]["final"]
        status = final["status"] if final else "(none: %s)" % run["outcome"]["stop_reason"]
        tool_count = 0
        for step in run["outcome"]["steps"]:
            if step.get("type") in ["tool_call", "final_answer"]:
                tool_count += 1
        usage = run["outcome"]["usage"]
        lines.append("| %s | %d | %s | %s | %s | %d | %d / %d | %.1f |" % (
            run["case"]["id"], run["repeat"], run["case"]["title"], status,
            "PASS" if run["verification"]["passed"] else "**FAIL**",
            tool_count, usage["prompt_tokens"], usage["output_tokens"], usage["wall_seconds"]))
    passed = 0
    for run in runs:
        if run["verification"]["passed"]:
            passed += 1
    lines.append("")
    lines.append("**Passed %d of %d runs.**" % (passed, len(runs)))
    lines.append("")

    for run in runs:
        case = run["case"]
        outcome = run["outcome"]
        lines.append("---")
        lines.append("")
        lines.append("## %s (run %d): %s" % (case["id"], run["repeat"], case["title"]))
        lines.append("")
        lines.append("**Question:** %s" % case["question"])
        lines.append("")
        lines.append("**Why we chose this case:** %s" % case["why_chosen"])
        if case.get("simulate_db_failure"):
            lines.append("")
            lines.append("**Test setup:** simulated database outage (every database tool returns an error).")
        lines.append("")
        lines.append("**Hand-checked expectation:** `%s`" % json.dumps(case["hand_checked"]))
        lines.append("")
        lines.append("### What the agent did")
        lines.append("")
        lines.append("| Step | Model's choice | Model's reason | Arguments | Result |")
        lines.append("|---|---|---|---|---|")
        for step in outcome["steps"]:
            if step["type"] == "tool_call":
                args = {}
                for key in step["arguments"]:
                    if key != "reason":
                        args[key] = step["arguments"][key]
                lines.append("| %d | `%s` | %s | %s | %s |" % (
                    step["step"], step["tool"], short(step["arguments"].get("reason", "")),
                    short(args, 220), short(result_summary(step["result"]), 220)))
            elif step["type"] == "final_answer":
                lines.append("| %d | `submit_answer` | %s | status: %s | (final) |" % (
                    step["step"], short(step["arguments"].get("reason", "")),
                    step["arguments"].get("status")))
            elif step["type"] == "text_only":
                lines.append("| %d | (text, no tool) | | %s | reminded to use a tool |" % (
                    step["step"], short(step.get("content", ""))))
            else:
                lines.append("| %d | %s | | %s | |" % (step["step"], step["type"], short(step.get("error", ""))))
        lines.append("")
        final = outcome["final"]
        lines.append("### Final answer")
        lines.append("")
        if final:
            lines.append("- **Status:** %s" % final["status"])
            lines.append("- **Answer:** %s" % final["answer"])
            lines.append("- **Key numbers:** %s" % final["key_numbers"])
            if final["assumptions"]:
                lines.append("- **Assumptions:** %s" % final["assumptions"])
            if final["sql_used"]:
                lines.append("- **SQL used:**")
                lines.append("")
                lines.append("```sql")
                lines.append(final["sql_used"])
                lines.append("```")
        else:
            lines.append("No final answer. Stop reason: %s." % outcome["stop_reason"])
        lines.append("")
        lines.append("### Verification (checked by Python, not by the model)")
        lines.append("")
        for check in run["verification"]["checks"]:
            lines.append("- %s **%s**: %s" % ("✅" if check["passed"] else "❌", check["check"],
                                              check["detail"]))
        for note in run["verification"]["notes"]:
            lines.append("- ℹ️ %s" % note)
        lines.append("")
        lines.append("**Result: %s**" % ("PASS" if run["verification"]["passed"] else "FAIL"))
        lines.append("")
        lines.append("**Our explanation (write in your own words):** _What does this run show? "
                     "Was the agent's final response justified by what the tools returned?_")
        lines.append("")

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", help="run only this case id, e.g. C2")
    parser.add_argument("--repeats", type=int, default=1, help="run each case this many times")
    parser.add_argument("--fake", action="store_true", help="use the scripted fake model (plumbing test only)")
    args = parser.parse_args()

    if not os.path.exists(db_tools.DB_PATH):
        print("Database not found. Run: python3 make_data.py")
        return

    if args.fake:
        from tests import fake_model
        model_name = "SCRIPTED FAKE MODEL (plumbing test only)"
    else:
        import model_client
        model_name = model_client.model_description()

    selected = []
    for case in cases.build_cases():
        if args.case is None or case["id"] == args.case:
            selected.append(case)
    if not selected:
        print("No case with id", args.case)
        return

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(HERE, "runs", "run_" + stamp + ("_FAKE" if args.fake else ""))
    os.makedirs(run_dir, exist_ok=True)

    print("Model:", model_name)
    print("Writing results to", run_dir)
    runs = []
    for case in selected:
        for repeat in range(1, args.repeats + 1):
            print("")
            print("=" * 78)
            print("%s (run %d): %s" % (case["id"], repeat, case["title"]))
            print("Question:", case["question"])
            if case.get("simulate_db_failure"):
                print("Setup: simulated database outage")
            print("-" * 78)

            context = {"simulate_db_failure": case.get("simulate_db_failure", False)}
            if args.fake:
                model_call = fake_model.make_fake_model(case["id"])
            else:
                model_call = model_client.call_ollama

            hash_before = verify.file_hash(db_tools.DB_PATH)
            outcome = agent.run_agent(case["question"], model_call, context)
            hash_after = verify.file_hash(db_tools.DB_PATH)
            verification = verify.verify_case(case, outcome, hash_before, hash_after)

            print("-" * 78)
            for check in verification["checks"]:
                print("  %s %s: %s" % ("PASS" if check["passed"] else "FAIL", check["check"], check["detail"]))
            for note in verification["notes"]:
                print("  NOTE", note)
            print("  RESULT:", "PASS" if verification["passed"] else "FAIL")

            runs.append({"case": case, "repeat": repeat, "outcome": outcome, "verification": verification})

    run_info = {"date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "model": model_name, "fake": args.fake}

    with open(os.path.join(run_dir, "trace.jsonl"), "w") as f:
        for run in runs:
            f.write(json.dumps({"case_id": run["case"]["id"], "repeat": run["repeat"],
                                "question": run["case"]["question"], "outcome": run["outcome"],
                                "verification": run["verification"]}, default=str) + "\n")

    summary = []
    passed = 0
    for run in runs:
        if run["verification"]["passed"]:
            passed += 1
        summary.append({"case_id": run["case"]["id"], "repeat": run["repeat"],
                        "passed": run["verification"]["passed"],
                        "final_status": run["outcome"]["final"]["status"] if run["outcome"]["final"] else None,
                        "usage": run["outcome"]["usage"]})
    with open(os.path.join(run_dir, "results.json"), "w") as f:
        json.dump({"run_info": run_info, "passed": passed, "total": len(runs), "runs": summary}, f, indent=2)

    write_record(os.path.join(run_dir, "RUN_RECORD.md"), run_info, runs)

    print("")
    print("=" * 78)
    print("Passed %d of %d runs. Record: %s" % (passed, len(runs), os.path.join(run_dir, "RUN_RECORD.md")))


if __name__ == "__main__":
    main()
