"""
agent.py - the agent loop.

Owner: Swathi (agent)

How it works:
    1. The model gets the question plus the list of tools.
    2. The model decides which tool to call (or to finish).
    3. Python checks and runs the tool, then sends the result back.
    4. The model reads the result and decides the next step.
    5. This repeats until the model calls submit_answer or hits the step limit.

Python never chooses the tools. It only runs what the model asks for and
refuses anything that is not allowed.

Ask a single question:
    python3 agent.py "How many auto loans are late?"
"""

import json
import sys
import time

import tools

MAX_STEPS = 10
MAX_NUDGES = 2

SYSTEM_PROMPT = """You are a loan portfolio analyst agent. You answer questions about a
fictional loan database by calling tools. Rules:

1. Never invent numbers. Every number in your answer must come from a run_sql result.
2. Call get_schema if you are unsure of table or column names.
3. Before filtering on a text value (status, product, state), check that the exact
   value exists with get_distinct_values, unless you have already seen it.
4. Compute percentages, averages and totals inside SQL (for example
   ROUND(100.0 * SUM(status = 'x') / COUNT(*), 2)), so one query result contains
   every number you report. Do not do arithmetic in your head.
5. If a query correctly returns no matching loans (or a count of 0), report that
   with status no_matching_loans. Do not guess.
6. If the question uses a term that does not exist in the data, or is too vague,
   either answer with a clearly stated assumption (put it in assumptions) or use
   status needs_clarification and say what you need to know.
7. You can only read data. If asked to change, delete, or add data, do not try:
   use status refused and explain.
8. If a tool keeps failing and you cannot get the data, use status unable and
   say what went wrong. Never report numbers you did not get from a tool.
9. If a query has an error, read the error message, fix the query, and try again.
10. Read every tool result fully. If a result has warnings, act on them before
    answering (for example, a filter value that does not exist in the data).
11. Only add filters the question asks for. If you add one anyway, say so in
    assumptions. "Outstanding balance" means the balance column, for any status.
12. Finish by calling submit_answer exactly once. In it, key_numbers must list every
    number in your answer, and sql_used must be a query you already ran."""


def short(value, limit=300):
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    if len(text) > limit:
        return text[:limit] + " ...(%d more chars)" % (len(text) - limit)
    return text


def say(printer, text):
    if printer:
        printer(text)


def describe_result(result):
    if not result.get("ok"):
        return "ERROR -> " + result.get("error", "")
    if "rows" in result:
        text = "%d row(s): %s" % (result["row_count"], short(result["rows"], 200))
        for warning in result.get("warnings", []):
            text = text + "\n           WARNING: " + warning
        return text
    if "values" in result:
        return "%d distinct value(s): %s" % (result["distinct_count"], short(result["values"], 200))
    return "ok (schema returned)"


def run_agent(question, model_call, context=None, printer=print, max_steps=MAX_STEPS):
    """Run the agent on one question.

    Returns a dictionary with:
        final        - the cleaned submit_answer arguments, or None
        stop_reason  - submitted / step_limit / model_error
        steps        - every model decision and tool call, in order (the trace)
        usage        - total tokens and time
    """
    if context is None:
        context = {}
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    steps = []
    totals = {"prompt_tokens": 0, "output_tokens": 0, "model_seconds": 0.0, "wall_seconds": 0.0}
    nudges = 0
    final = None
    stop_reason = "step_limit"
    started = time.time()

    for step_number in range(1, max_steps + 1):
        try:
            reply = model_call(messages, tools.TOOL_SPECS)
        except Exception as exc:
            say(printer, "  [step %d] MODEL ERROR: %s" % (step_number, exc))
            steps.append({"step": step_number, "type": "model_error", "error": str(exc)})
            stop_reason = "model_error"
            break

        usage = reply.get("usage", {})
        totals["prompt_tokens"] += usage.get("prompt_tokens", 0)
        totals["output_tokens"] += usage.get("output_tokens", 0)
        totals["model_seconds"] += usage.get("model_seconds", 0.0)

        messages.append(reply["raw_message"])

        if not reply["tool_calls"]:
            # The model wrote text instead of using a tool. Remind it once or twice.
            say(printer, "  [step %d] Model wrote text without calling a tool: %s"
                % (step_number, short(reply["content"], 200)))
            steps.append({"step": step_number, "type": "text_only", "content": reply["content"]})
            if nudges >= MAX_NUDGES:
                stop_reason = "no_tool_call"
                break
            nudges += 1
            messages.append({"role": "user", "content":
                             "Please continue by calling a tool. When you are done, call submit_answer."})
            continue

        for call in reply["tool_calls"]:
            name = call["name"]
            args = call["arguments"] if isinstance(call["arguments"], dict) else {}
            reason = args.get("reason", "(no reason given)")

            say(printer, "  [step %d] Model chose: %s" % (step_number, name))
            say(printer, "           Reason: %s" % reason)

            if name == "submit_answer":
                cleaned, problem = tools.check_final_answer(args)
                if problem:
                    say(printer, "           Python refused the answer: " + problem)
                    result = {"ok": False, "error": "submit_answer was not accepted: " + problem}
                    steps.append({"step": step_number, "type": "tool_call", "tool": name,
                                  "arguments": args, "result": result})
                    messages.append({"role": "tool", "tool_name": name, "content": json.dumps(result)})
                    continue
                say(printer, "           Status: %s" % cleaned["status"])
                say(printer, "           Answer: %s" % cleaned["answer"])
                if cleaned["assumptions"]:
                    say(printer, "           Assumptions: %s" % cleaned["assumptions"])
                steps.append({"step": step_number, "type": "final_answer", "tool": name, "arguments": args})
                final = cleaned
                stop_reason = "submitted"
                break

            shown_args = {}
            for key in args:
                if key != "reason":
                    shown_args[key] = args[key]
            if shown_args:
                say(printer, "           Arguments: %s" % short(shown_args, 400))

            result = tools.execute_tool(name, args, context)
            say(printer, "           Result: %s" % describe_result(result))
            steps.append({"step": step_number, "type": "tool_call", "tool": name,
                          "arguments": args, "result": result})
            messages.append({"role": "tool", "tool_name": name, "content": json.dumps(result, default=str)})

        if final is not None:
            break

    totals["wall_seconds"] = round(time.time() - started, 2)
    totals["model_seconds"] = round(totals["model_seconds"], 2)
    if final is None and stop_reason == "step_limit":
        say(printer, "  Stopped: reached the limit of %d steps without a final answer." % max_steps)
    return {"final": final, "stop_reason": stop_reason, "steps": steps, "usage": totals}


if __name__ == "__main__":
    import model_client

    if len(sys.argv) < 2:
        print('Usage: python3 agent.py "your question"')
        sys.exit(1)
    print("Model:", model_client.model_description())
    print("Question:", sys.argv[1])
    outcome = run_agent(sys.argv[1], model_client.call_ollama)
    print("Stop reason:", outcome["stop_reason"], "| usage:", outcome["usage"])
