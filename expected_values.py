"""
expected_values.py - the hand-checked answers.

Owner: Sachin (evaluation)

These answers are computed in plain Python straight from the CSV files.
No SQL and no language model is used here, so they are an INDEPENDENT
check on the agent. If the agent and this file disagree, the test fails.

Run on its own to print the expected answers:
    python3 expected_values.py
"""

import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")


def load_rows(filename):
    rows = []
    with open(os.path.join(DATA_DIR, filename)) as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def load_data():
    borrowers = {}
    for row in load_rows("borrowers.csv"):
        borrowers[row["borrower_id"]] = row
    loans = load_rows("loans.csv")
    return borrowers, loans


def default_count_and_percent():
    """C1: How many loans are in default, and what percent of all loans?"""
    borrowers, loans = load_data()
    defaults = 0
    for loan in loans:
        if loan["status"] == "default":
            defaults = defaults + 1
    percent = round(defaults * 100.0 / len(loans), 2)
    return {"default_count": defaults, "total_loans": len(loans), "default_percent": percent}


def top_state_mortgage_balance():
    """C2: Which state has the highest outstanding mortgage balance?"""
    borrowers, loans = load_data()
    totals = {}
    for loan in loans:
        if loan["product"] == "mortgage":
            state = borrowers[loan["borrower_id"]]["state"]
            totals[state] = totals.get(state, 0.0) + float(loan["balance"])
    best_state = None
    for state in totals:
        if best_state is None or totals[state] > totals[best_state]:
            best_state = state
    return {"state": best_state, "balance": round(totals[best_state], 2)}


def mortgages_below_580():
    """C3: How many mortgages went to borrowers with credit score below 580?"""
    borrowers, loans = load_data()
    count = 0
    for loan in loans:
        score = int(borrowers[loan["borrower_id"]]["credit_score"])
        if loan["product"] == "mortgage" and score < 580:
            count = count + 1
    return {"count": count}


def personal_loans_in_default():
    """C4: There is no 'charged_off' status. The closest status is 'default'."""
    borrowers, loans = load_data()
    count = 0
    for loan in loans:
        if loan["product"] == "personal" and loan["status"] == "default":
            count = count + 1
    return {"count": count}

def avg_rate_auto_2023():
    """C7: Average interest rate on auto loans originated in 2023."""
    borrowers, loans = load_data()
    total = 0.0
    count = 0
    for loan in loans:
        year = loan["origination_date"][:4]   # dates look like 2023-07-14
        if loan["product"] == "auto" and year == "2023":
            total = total + float(loan["interest_rate"])
            count = count + 1
    average = round(total / count, 2)
    return {"average_rate": average, "loan_count": count}


def highest_default_rate_product():
    """C8: Which product has the highest default rate (defaults / loans of that product)?"""
    borrowers, loans = load_data()
    totals = {}
    defaults = {}
    for loan in loans:
        product = loan["product"]
        totals[product] = totals.get(product, 0) + 1
        if loan["status"] == "default":
            defaults[product] = defaults.get(product, 0) + 1

    rates = {}
    for product in totals:
        rates[product] = defaults.get(product, 0) * 100.0 / totals[product]

    best_product = None
    for product in rates:
        if best_product is None or rates[product] > rates[best_product]:
            best_product = product

    # Check that no other product has exactly the same rate (a tie would make the question ambiguous).
    tied = []
    for product in rates:
        if rates[product] == rates[best_product]:
            tied.append(product)

    rounded_rates = {}
    for product in rates:
        rounded_rates[product] = round(rates[product], 2)

    return {
        "product": best_product,
        "default_percent": round(rates[best_product], 2),
        "default_count": defaults.get(best_product, 0),
        "product_loans": totals[best_product],
        "all_rates": rounded_rates,
        "tie": len(tied) > 1,
    }


def all_statuses():
    borrowers, loans = load_data()
    statuses = []
    for loan in loans:
        if loan["status"] not in statuses:
            statuses.append(loan["status"])
    return sorted(statuses)


if __name__ == "__main__":
    print("C1 default count and percent:", default_count_and_percent())
    print("C2 top state mortgage balance:", top_state_mortgage_balance())
    print("C3 mortgages below 580:", mortgages_below_580())
    print("C4 personal loans in default:", personal_loans_in_default())
    print("C7 average auto rate 2023:", avg_rate_auto_2023())
    print("C8 highest default rate product:", highest_default_rate_product())
    print("Statuses in the data:", all_statuses())
