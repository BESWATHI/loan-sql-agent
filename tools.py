"""
tools.py - the tool descriptions the model sees, and the code that runs them.

Owner: Swathi (agent and safety)

Every tool has a required "reason" argument. The model must say WHY it is
calling the tool, so the trace shows the model's decisions, not just its
actions.
"""

import db_tools

FINAL_STATUSES = ["answered", "no_matching_loans", "needs_clarification", "refused", "unable"]

REASON_PARAM = {
    "type": "string",
    "description": "One short sentence: why you are calling this tool now.",
}


def tool(name, description, properties, required):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required},
        },
    }


TOOL_SPECS = [
    tool(
        "get_schema",
        "Describe the tables and columns in the loan database.",
        {"reason": REASON_PARAM},
        ["reason"],
    ),
    tool(
        "get_distinct_values",
        "List the values that actually exist in one column, with counts. "
        "Use this before filtering on a text value (like a status, product or state) "
        "if you are not sure the exact spelling exists in the data.",
        {
            "reason": REASON_PARAM,
            "table": {"type": "string", "description": "borrowers or loans"},
            "column": {"type": "string", "description": "Column name from the schema"},
        },
        ["reason", "table", "column"],
    ),
    tool(
        "run_sql",
        "Run ONE read-only SQLite SELECT query and return the rows. "
        "Writing or changing data is blocked.",
        {
            "reason": REASON_PARAM,
            "query": {"type": "string", "description": "A single SQLite SELECT statement"},
        },
        ["reason", "query"],
    ),
    tool(
        "submit_answer",
        "Finish the task. Call this exactly once, at the end.",
        {
            "reason": REASON_PARAM,
            "status": {
                "type": "string",
                "enum": FINAL_STATUSES,
                "description": (
                    "answered = you answered from query results; "
                    "no_matching_loans = the query correctly found no matching loans; "
                    "needs_clarification = the question is too unclear to answer safely; "
                    "refused = the request asks to change data or is not allowed; "
                    "unable = a tool failed and you could not get the data"
                ),
            },
            "answer": {"type": "string", "description": "Plain-English answer for a business user"},
            "key_numbers": {
                "type": "array",
                "items": {"type": "number"},
                "description": ("Every number that appears in your answer (counts, totals, "
                                "percentages), copied exactly from run_sql results. Empty if none."),
            },
            "sql_used": {
                "type": "string",
                "description": ("A query you ALREADY RAN with run_sql whose result contains your "
                                "key numbers. Do not write a new query here. Empty if none."),
            },
            "assumptions": {
                "type": "string",
                "description": "Any assumption you made about the meaning of the question. Empty if none.",
            },
        },
        ["reason", "status", "answer", "key_numbers", "sql_used", "assumptions"],
    ),
]


def execute_tool(name, args, context):
    """Run a (non-final) tool and return its result as a dictionary."""
    if name == "get_schema":
        return db_tools.get_schema(context)
    if name == "get_distinct_values":
        if "table" not in args or "column" not in args:
            return {"ok": False, "error": "get_distinct_values needs both table and column."}
        return db_tools.get_distinct_values(args["table"], args["column"], context)
    if name == "run_sql":
        if "query" not in args:
            return {"ok": False, "error": "run_sql needs a query."}
        return db_tools.run_sql(args["query"], context)
    return {"ok": False, "error": "Unknown tool: " + str(name)}


def to_number(value):
    """Turn things like 5.5, "5.5", "$4,332,437.74" or "5.5%" into a float."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.replace(",", "").replace("$", "").replace("%", "").strip()
        try:
            return float(text)
        except ValueError:
            return None
    return None


def check_final_answer(args):
    """Validate submit_answer arguments. Returns (cleaned_answer, error_message)."""
    status = args.get("status")
    if status not in FINAL_STATUSES:
        return None, "status must be one of: " + ", ".join(FINAL_STATUSES)
    answer = args.get("answer")
    if not isinstance(answer, str) or answer.strip() == "":
        return None, "answer must be a non-empty string."

    raw_numbers = args.get("key_numbers") or []
    if not isinstance(raw_numbers, list):
        raw_numbers = [raw_numbers]
    numbers = []
    for item in raw_numbers:
        number = to_number(item)
        if number is None:
            return None, "key_numbers must contain only numbers (got %r)." % (item,)
        numbers.append(number)

    cleaned = {
        "status": status,
        "answer": answer.strip(),
        "key_numbers": numbers,
        "sql_used": (args.get("sql_used") or "").strip(),
        "assumptions": (args.get("assumptions") or "").strip(),
        "reason": (args.get("reason") or "").strip(),
    }
    return cleaned, None
