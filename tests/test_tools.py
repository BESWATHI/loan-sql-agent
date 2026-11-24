"""
tests/test_tools.py - direct tests of the tools and the read-only guard.

Owner: Swathi (safety)

These call the tools directly, with no language model, so they prove the
guard works no matter what the model decides.

Run from the main project folder:
    python3 -m tests.test_tools
"""

import db_tools
import verify

results = []


def check(name, condition, detail):
    results.append(condition)
    print("%s  %s" % ("PASS" if condition else "FAIL", name))
    print("      " + detail)


def blocked(query, **kwargs):
    result = db_tools.run_sql(query, **kwargs)
    return (not result["ok"]), result.get("error", str(result))


def main():
    hash_before = verify.file_hash(db_tools.DB_PATH)

    r = db_tools.run_sql("SELECT COUNT(*) FROM loans")
    check("Normal SELECT works", r["ok"] and r["rows"] == [[600]], str(r["rows"]))

    r = db_tools.run_sql("WITH t AS (SELECT status FROM loans) SELECT COUNT(*) FROM t")
    check("WITH (CTE) query works", r["ok"] and r["rows"] == [[600]], str(r.get("rows")))

    for query in [
        "DELETE FROM loans WHERE status = 'paid_off'",
        "UPDATE loans SET balance = 0",
        "DROP TABLE loans",
        "INSERT INTO loans (loan_id) VALUES (9999)",
        "PRAGMA table_info(loans)",
        "ATTACH DATABASE 'other.db' AS other",
        "SELECT 1; DELETE FROM loans",
        "SELECT name FROM sqlite_master",
        "SELECT * FROM pragma_table_info('loans')",
        "WITH x AS (SELECT 1) DELETE FROM loans",
    ]:
        is_blocked, message = blocked(query)
        check("Blocked: " + query, is_blocked, message)

    is_blocked, message = blocked(
        "WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM c) SELECT COUNT(*) FROM c",
        timeout_seconds=1.0)
    check("Runaway query is stopped by the time limit", is_blocked and "longer than" in message, message)

    r = db_tools.run_sql("SELECT * FROM loans")
    check("Row limit applied", r["ok"] and r["row_count"] == db_tools.MAX_ROWS and r["truncated"],
          "row_count=%s truncated=%s" % (r.get("row_count"), r.get("truncated")))

    r = db_tools.run_sql("SELECT loan_status FROM loans")
    check("Bad column returns a helpful error", (not r["ok"]) and "loan_status" in r["error"], r.get("error", ""))

    r = db_tools.get_distinct_values("loans", "status")
    values = []
    for item in r.get("values", []):
        values.append(item["value"])
    check("get_distinct_values lists real statuses",
          r["ok"] and sorted(values) == ["current", "default", "late", "paid_off"], str(values))

    r = db_tools.get_distinct_values("loans", "status; DROP TABLE loans")
    check("get_distinct_values refuses unknown columns", not r["ok"], r.get("error", ""))

    r = db_tools.run_sql("SELECT COUNT(*) FROM loans WHERE status = 'charged-off'")
    check("Refused: filter on a status that does not exist",
          (not r["ok"]) and "charged-off" in r["error"] and "default" in r["error"], r.get("error", ""))

    r = db_tools.run_sql("SELECT COUNT(*) FROM loans l WHERE l.product = 'Mortgage'")
    check("Refused: wrong capitalization of a product", (not r["ok"]) and "'Mortgage'" in r["error"],
          r.get("error", ""))

    r = db_tools.run_sql("SELECT COUNT(*) FROM loans WHERE status IN ('default', 'charged_off')")
    check("Refused: one bad value inside IN (...)", (not r["ok"]) and "charged_off" in r["error"],
          r.get("error", ""))

    r = db_tools.run_sql("SELECT SUM(status = 'charged-off'), "
                         "SUM(product = 'personal' AND status = 'charged-off') FROM loans")
    check("Refused: same bad value used twice gives one warning",
          (not r["ok"]) and r["error"].count("'charged-off' does not exist") == 1, r.get("error", ""))

    r = db_tools.run_sql("SELECT COUNT(*) FROM loans WHERE status = 'charged-off' OR status = 'written-off'")
    check("Refused: two different bad values each get a warning",
          (not r["ok"]) and "'charged-off'" in r["error"] and "'written-off'" in r["error"],
          r.get("error", ""))

    r = db_tools.run_sql("SELECT COUNT(*) FROM loans WHERE product = 'personal' AND status IN ('default', 'late')")
    check("Allowed: all filter values exist", r["ok"] and r["rows"] == [[15]] if r["ok"] else False,
          str(r.get("rows", r.get("error"))))

    r = db_tools.run_sql("SELECT COUNT(*) FROM loans WHERE product LIKE 'mort%'")
    check("Allowed: LIKE patterns are not checked", r["ok"], str(r.get("rows", r.get("error"))))

    r = db_tools.run_sql("SELECT 1", context={"simulate_db_failure": True})
    check("Simulated outage returns an error", (not r["ok"]) and "unavailable" in r["error"], r.get("error", ""))

    hash_after = verify.file_hash(db_tools.DB_PATH)
    check("Database file unchanged after all tests", hash_before == hash_after, "SHA-256 before == after")

    passed = 0
    for item in results:
        if item:
            passed += 1
    print("")
    print("%d of %d tests passed." % (passed, len(results)))


if __name__ == "__main__":
    main()
