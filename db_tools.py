"""
db_tools.py - the tools the agent can use, plus the read-only guard.

Owner: Swathi (agent and safety)

Tools:
    get_schema()                         -> describes the fixed schema
    get_distinct_values(table, column)   -> which values actually exist
    run_sql(query)                       -> runs ONE read-only SELECT query

Safety layers in run_sql (each one is tested in tests/test_tools.py):
    1. The query must start with SELECT or WITH.
    2. The database is opened in read-only mode.
    3. A SQLite "authorizer" refuses every action except reading the two
       approved tables (so no INSERT, UPDATE, DELETE, DROP, PRAGMA, ATTACH,
       and no reading hidden tables like sqlite_master).
    4. Only one statement per call.
    5. A time limit stops runaway queries.
    6. A row limit stops huge results.
    7. Filters on values that do not exist (status = 'charged-off') are refused,
       with the real values listed, instead of silently returning 0.
"""

import os
import re
import sqlite3
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "data", "loans.db")

ALLOWED_TABLES = ["borrowers", "loans"]
MAX_ROWS = 200
QUERY_TIMEOUT_SECONDS = 3.0

SCHEMA = {
    "borrowers": {
        "description": "One row per borrower (fictional people).",
        "columns": [
            ["borrower_id", "INTEGER", "Unique borrower id"],
            ["state", "TEXT", "Two-letter US state code where the borrower lives"],
            ["credit_score", "INTEGER", "Credit score from 300 to 850"],
            ["annual_income", "REAL", "Yearly income in US dollars"],
        ],
    },
    "loans": {
        "description": "One row per loan. Join to borrowers on borrower_id.",
        "columns": [
            ["loan_id", "INTEGER", "Unique loan id"],
            ["borrower_id", "INTEGER", "The borrower who holds the loan"],
            ["product", "TEXT", "Loan type. Use get_distinct_values to see the exact values"],
            ["origination_date", "TEXT", "Date the loan was issued, as YYYY-MM-DD"],
            ["amount", "REAL", "Original loan amount in US dollars"],
            ["interest_rate", "REAL", "Annual interest rate in percent, e.g. 6.25 means 6.25%"],
            ["term_months", "INTEGER", "Length of the loan in months"],
            ["status", "TEXT", "Loan status. Use get_distinct_values to see the exact values"],
            ["balance", "REAL", "Outstanding (unpaid) principal in US dollars. Paid-off loans have 0"],
        ],
    },
}

# SQLite authorizer action codes (with fallbacks for older Python versions).
SQLITE_OK = sqlite3.SQLITE_OK
SQLITE_DENY = sqlite3.SQLITE_DENY
ACTION_SELECT = getattr(sqlite3, "SQLITE_SELECT", 21)
ACTION_READ = getattr(sqlite3, "SQLITE_READ", 20)
ACTION_FUNCTION = getattr(sqlite3, "SQLITE_FUNCTION", 31)
ACTION_RECURSIVE = getattr(sqlite3, "SQLITE_RECURSIVE", 33)

# Text columns with a small set of fixed values. If a query filters on a value
# that is not in the data, run_sql refuses the query and lists the real values.
CATEGORY_COLUMNS = {"status": "loans", "product": "loans", "state": "borrowers"}

# Matches  status = 'x'   l.product='x'   status IN ('a', 'b')   status LIKE 'x'
EQUALS_PATTERN = re.compile(r"(?:\w+\.)?(\w+)\s*(?:=|==|LIKE)\s*'([^']*)'", re.IGNORECASE)
IN_PATTERN = re.compile(r"(?:\w+\.)?(\w+)\s+IN\s*\(([^)]*)\)", re.IGNORECASE)

SIMULATED_FAILURE_MESSAGE = (
    "Database connection failed: the loan database is unavailable right now "
    "(simulated outage for testing)."
)


def read_only_authorizer(action, arg1, arg2, db_name, trigger):
    """Called by SQLite for every action a query tries to take."""
    if action == ACTION_SELECT:
        return SQLITE_OK
    if action == ACTION_READ:
        # arg1 is the name of the table being read.
        table = (arg1 or "").lower()
        if table.startswith("sqlite_"):
            return SQLITE_DENY          # hidden system tables
        if table in ALLOWED_TABLES:
            return SQLITE_OK            # the two approved tables
        if db_name is None:
            return SQLITE_OK            # a WITH (CTE) name defined inside the query
        return SQLITE_DENY              # any other real table
    if action == ACTION_FUNCTION:
        return SQLITE_OK
    if action == ACTION_RECURSIVE:
        return SQLITE_OK
    return SQLITE_DENY


def open_read_only(timeout_seconds):
    """Open the database read-only, with the authorizer and a time limit."""
    uri = "file:" + DB_PATH + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    deadline = time.time() + timeout_seconds

    def stop_if_too_slow():
        # Returning a non-zero value tells SQLite to stop the query.
        if time.time() > deadline:
            return 1
        return 0

    conn.set_progress_handler(stop_if_too_slow, 1000)
    conn.set_authorizer(read_only_authorizer)
    return conn


def error(message):
    return {"ok": False, "error": message}


def explain_sqlite_error(exc, timeout_seconds):
    text = str(exc)
    if "not authorized" in text or "prohibited" in text:
        return ("Blocked by the read-only guard: this query tried to do something other than "
                "read the borrowers and loans tables. (" + text + ")")
    if "interrupted" in text:
        return "Query stopped: it ran longer than %.1f seconds." % timeout_seconds
    if "one statement at a time" in text:
        return "Blocked: only one SQL statement is allowed per call."
    if "readonly" in text:
        return "Blocked: the database is read-only. (" + text + ")"
    return "SQL error: " + text


def get_schema(context=None):
    return {"ok": True, "tables": SCHEMA}


def column_exists(table, column):
    if table not in SCHEMA:
        return False
    for col in SCHEMA[table]["columns"]:
        if col[0] == column:
            return True
    return False


def get_distinct_values(table, column, context=None, limit=50):
    if context and context.get("simulate_db_failure"):
        return error(SIMULATED_FAILURE_MESSAGE)
    if not column_exists(table, column):
        return error("Unknown table or column: %s.%s. Call get_schema to see valid names." % (table, column))

    # Safe to build the query this way only because table and column were
    # checked against the fixed schema above.
    query = ("SELECT " + column + ", COUNT(*) FROM " + table +
             " GROUP BY " + column + " ORDER BY COUNT(*) DESC")
    conn = open_read_only(QUERY_TIMEOUT_SECONDS)
    try:
        rows = conn.execute(query).fetchall()
    except Exception as exc:
        return error(explain_sqlite_error(exc, QUERY_TIMEOUT_SECONDS))
    finally:
        conn.close()

    values = []
    for row in rows[:limit]:
        values.append({"value": row[0], "count": row[1]})
    return {
        "ok": True,
        "table": table,
        "column": column,
        "distinct_count": len(rows),
        "values": values,
        "truncated": len(rows) > limit,
    }


def existing_values(column):
    table = CATEGORY_COLUMNS[column]
    conn = open_read_only(QUERY_TIMEOUT_SECONDS)
    try:
        rows = conn.execute("SELECT DISTINCT " + column + " FROM " + table).fetchall()
    finally:
        conn.close()
    values = []
    for row in rows:
        values.append(row[0])
    return sorted(values)


def filter_value_warnings(query):
    """Find text filters like status = 'charged-off' whose value is not in the data."""
    pairs = []
    for column, value in EQUALS_PATTERN.findall(query):
        pairs.append((column.lower(), value))
    for column, inside in IN_PATTERN.findall(query):
        for value in re.findall(r"'([^']*)'", inside):
            pairs.append((column.lower(), value))

    warnings = []
    for column, value in pairs:
        if column not in CATEGORY_COLUMNS:
            continue
        if "%" in value:
            continue  # LIKE patterns such as 'mort%' are not checked
        values = existing_values(column)
        if value not in values:
            message = ("The value '%s' does not exist in %s.%s. Existing values are: %s."
                       % (value, CATEGORY_COLUMNS[column], column, ", ".join(values)))
            if message not in warnings:  # the same bad value used twice gives one warning
                warnings.append(message)
    return warnings


def run_sql(query, context=None, timeout_seconds=QUERY_TIMEOUT_SECONDS):
    if context and context.get("simulate_db_failure"):
        return error(SIMULATED_FAILURE_MESSAGE)
    if not isinstance(query, str) or query.strip() == "":
        return error("The query is empty.")

    cleaned = query.strip()
    while cleaned.endswith(";"):
        cleaned = cleaned[:-1].strip()

    first_word = cleaned.split()[0].upper()
    if first_word not in ["SELECT", "WITH"]:
        return error("Blocked by the read-only guard: only SELECT queries are allowed "
                     "(the query started with " + first_word + ").")

    # Refuse filters on values that do not exist, so the model never receives a
    # misleading 0 (for example status = 'charged-off' when there is no such status).
    bad_filters = filter_value_warnings(cleaned)
    if bad_filters:
        return error(
            "Query refused: it filters on a value that is not in the data. "
            + " ".join(bad_filters)
            + " Fix the filter. If the question uses a term that is not in the data, either "
              "answer using an existing value and state that assumption, or use status "
              "needs_clarification.")

    conn = open_read_only(timeout_seconds)
    try:
        cursor = conn.execute(cleaned)
        rows = cursor.fetchmany(MAX_ROWS + 1)
        columns = []
        for item in cursor.description:
            columns.append(item[0])
    except Exception as exc:
        return error(explain_sqlite_error(exc, timeout_seconds))
    finally:
        conn.close()

    truncated = len(rows) > MAX_ROWS
    result_rows = []
    for row in rows[:MAX_ROWS]:
        result_rows.append(list(row))
    result = {
        "ok": True,
        "columns": columns,
        "rows": result_rows,
        "row_count": len(result_rows),
        "truncated": truncated,
        "note": ("Only the first %d rows are shown." % MAX_ROWS) if truncated else "",
    }
    return result
