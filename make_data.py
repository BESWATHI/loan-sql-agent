"""
make_data.py - builds the synthetic (fictional) loan database.

Owner: Sachin (data)

Everything here is made up. A fixed random seed means every run creates
exactly the same data, so the hand-checked answers never change.

Creates:
    data/borrowers.csv   data/loans.csv   (plain files, used for hand-checking)
    data/loans.db        (SQLite database, used by the agent)

Run:
    python3 make_data.py
"""

import csv
import os
import random
import sqlite3

SEED = 7374
NUM_BORROWERS = 300
NUM_LOANS = 600

STATES = ["MA", "NY", "CA", "TX", "FL", "IL", "OH", "WA"]
PRODUCTS = ["mortgage", "auto", "personal", "student"]
PRODUCT_WEIGHTS = [3, 4, 4, 2]

# Underwriting rule built into the data: no mortgage is ever issued to a
# borrower with a credit score below this. Test case C3 depends on it.
MORTGAGE_MIN_SCORE = 580

AMOUNT_RANGE = {
    "mortgage": (120000, 650000),
    "auto": (8000, 60000),
    "personal": (2000, 40000),
    "student": (5000, 90000),
}
TERM_CHOICES = {
    "mortgage": [180, 360],
    "auto": [36, 48, 60, 72],
    "personal": [24, 36, 60],
    "student": [120],
}
BASE_RATE = {"mortgage": 5.5, "auto": 6.5, "personal": 11.0, "student": 6.0}

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")


def clamp(value, low, high):
    if value < low:
        return low
    if value > high:
        return high
    return value


def make_borrowers(rng):
    borrowers = []
    for borrower_id in range(1, NUM_BORROWERS + 1):
        score = clamp(int(rng.gauss(690, 70)), 300, 850)
        income = int(rng.lognormvariate(11.0, 0.45) / 100) * 100
        borrowers.append({
            "borrower_id": borrower_id,
            "state": rng.choice(STATES),
            "credit_score": score,
            "annual_income": income,
        })
    return borrowers


def pick_status(rng, score):
    # Lower credit score -> higher chance of default.
    p_default = 0.02 + max(0, 680 - score) * 0.0015
    r = rng.random()
    if r < p_default:
        return "default"
    if r < p_default + 0.05:
        return "late"
    if r < p_default + 0.30:
        return "paid_off"
    return "current"


def make_loans(rng, borrowers):
    loans = []
    for loan_id in range(1, NUM_LOANS + 1):
        borrower = rng.choice(borrowers)
        score = borrower["credit_score"]

        product = rng.choices(PRODUCTS, weights=PRODUCT_WEIGHTS)[0]
        if product == "mortgage" and score < MORTGAGE_MIN_SCORE:
            product = "personal"  # underwriting rule

        low, high = AMOUNT_RANGE[product]
        amount = round(rng.uniform(low, high), 2)
        term = rng.choice(TERM_CHOICES[product])
        rate = BASE_RATE[product] + (720 - score) * 0.02 + rng.uniform(-0.75, 0.75)
        rate = round(max(2.5, rate), 2)

        year = rng.randint(2019, 2024)
        month = rng.randint(1, 12)
        day = rng.randint(1, 28)
        date = "%d-%02d-%02d" % (year, month, day)

        status = pick_status(rng, score)
        if status == "paid_off":
            balance = 0.0
        elif status == "default":
            balance = round(amount * rng.uniform(0.3, 0.9), 2)
        else:
            balance = round(amount * rng.uniform(0.2, 0.95), 2)

        loans.append({
            "loan_id": loan_id,
            "borrower_id": borrower["borrower_id"],
            "product": product,
            "origination_date": date,
            "amount": amount,
            "interest_rate": rate,
            "term_months": term,
            "status": status,
            "balance": balance,
        })
    return loans


def write_csv(path, rows):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_sqlite(path, borrowers, loans):
    if os.path.exists(path):
        os.remove(path)
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE borrowers (
            borrower_id   INTEGER PRIMARY KEY,
            state         TEXT NOT NULL,
            credit_score  INTEGER NOT NULL,
            annual_income REAL NOT NULL
        )""")
    conn.execute("""
        CREATE TABLE loans (
            loan_id          INTEGER PRIMARY KEY,
            borrower_id      INTEGER NOT NULL REFERENCES borrowers(borrower_id),
            product          TEXT NOT NULL,
            origination_date TEXT NOT NULL,
            amount           REAL NOT NULL,
            interest_rate    REAL NOT NULL,
            term_months      INTEGER NOT NULL,
            status           TEXT NOT NULL,
            balance          REAL NOT NULL
        )""")
    for b in borrowers:
        conn.execute("INSERT INTO borrowers VALUES (?, ?, ?, ?)",
                     (b["borrower_id"], b["state"], b["credit_score"], b["annual_income"]))
    for l in loans:
        conn.execute("INSERT INTO loans VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (l["loan_id"], l["borrower_id"], l["product"], l["origination_date"],
                      l["amount"], l["interest_rate"], l["term_months"], l["status"], l["balance"]))
    conn.commit()
    conn.close()


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    rng = random.Random(SEED)
    borrowers = make_borrowers(rng)
    loans = make_loans(rng, borrowers)
    write_csv(os.path.join(DATA_DIR, "borrowers.csv"), borrowers)
    write_csv(os.path.join(DATA_DIR, "loans.csv"), loans)
    write_sqlite(os.path.join(DATA_DIR, "loans.db"), borrowers, loans)
    print("Created %d borrowers and %d loans in %s" % (len(borrowers), len(loans), DATA_DIR))


if __name__ == "__main__":
    main()
