"""
Generates a synthetic but realistic banking dataset:
customers, accounts, transactions.
Deliberately includes some messiness (nulls, a few duplicate rows,
inconsistent category casing) so the SQL/EDA has real cleaning work to do.
"""
import numpy as np
import pandas as pd
import sqlite3
from pathlib import Path

rng = np.random.default_rng(42)
OUT = Path(__file__).resolve().parent.parent / "data"
OUT.mkdir(exist_ok=True)

# ---------- customers ----------
N_CUST = 400
segments = rng.choice(["Retail", "Premium", "Business"], size=N_CUST, p=[0.65, 0.25, 0.10])
cities = rng.choice(
    ["Hyderabad", "Mumbai", "Bengaluru", "Delhi", "Chennai", "Pune", "Kolkata"],
    size=N_CUST
)
signup_dates = pd.to_datetime("2022-01-01") + pd.to_timedelta(
    rng.integers(0, 1000, N_CUST), unit="D"
)
customers = pd.DataFrame({
    "customer_id": np.arange(1, N_CUST + 1),
    "segment": segments,
    "city": cities,
    "signup_date": signup_dates,
})

# ---------- accounts ----------
acct_rows = []
acct_id = 1
for cid in customers["customer_id"]:
    n_accts = rng.choice([1, 1, 1, 2], p=[0.55, 0.2, 0.1, 0.15])
    for _ in range(n_accts):
        acct_type = rng.choice(["Savings", "Current"], p=[0.8, 0.2])
        acct_rows.append({
            "account_id": acct_id,
            "customer_id": cid,
            "account_type": acct_type,
            "opened_date": customers.loc[customers.customer_id == cid, "signup_date"].values[0],
        })
        acct_id += 1
accounts = pd.DataFrame(acct_rows)

# ---------- transactions ----------
categories = ["Groceries", "Dining", "Utilities", "Travel", "Shopping",
              "Salary Credit", "ATM Withdrawal", "Transfer", "Entertainment", "Healthcare"]
# messy category variants to simulate real-world dirty data
category_variants = {
    "Groceries": ["Groceries", "groceries", "GROCERIES"],
    "Dining": ["Dining", "dining "],
    "Shopping": ["Shopping", "shopping"],
}

N_TXN = 20000
txn_customer = rng.choice(accounts["account_id"], size=N_TXN)
txn_date = pd.to_datetime("2024-01-01") + pd.to_timedelta(rng.integers(0, 545, N_TXN), unit="D")
txn_category_clean = rng.choice(categories, size=N_TXN, p=[.15,.12,.10,.08,.15,.05,.10,.10,.08,.07])

txn_category = []
for c in txn_category_clean:
    variants = category_variants.get(c, [c])
    txn_category.append(rng.choice(variants))

# amount: credits (salary) positive & larger, debits negative, with noise
amount = []
for c in txn_category_clean:
    if c == "Salary Credit":
        amount.append(rng.normal(45000, 8000))
    elif c == "Transfer":
        amount.append(rng.choice([-1, 1]) * rng.normal(5000, 3000))
    else:
        amount.append(-abs(rng.normal(1200, 900)))
amount = np.round(amount, 2)

transactions = pd.DataFrame({
    "transaction_id": np.arange(1, N_TXN + 1),
    "account_id": txn_customer,
    "txn_date": txn_date,
    "category": txn_category,
    "amount": amount,
})

# inject some nulls and duplicate rows to simulate real dirty data
null_idx = rng.choice(transactions.index, size=150, replace=False)
transactions.loc[null_idx, "category"] = None

dup_rows = transactions.sample(80, random_state=1)
transactions = pd.concat([transactions, dup_rows], ignore_index=True)

# save CSVs (raw / uncleaned -- cleaning happens in SQL views + notebook)
customers.to_csv(OUT / "customers.csv", index=False)
accounts.to_csv(OUT / "accounts.csv", index=False)
transactions.to_csv(OUT / "transactions.csv", index=False)

# load into SQLite
db_path = OUT / "bank.db"
conn = sqlite3.connect(db_path)
customers.to_sql("customers", conn, if_exists="replace", index=False)
accounts.to_sql("accounts", conn, if_exists="replace", index=False)
transactions.to_sql("transactions", conn, if_exists="replace", index=False)
conn.close()

print(f"customers: {len(customers)}, accounts: {len(accounts)}, transactions: {len(transactions)}")
print(f"SQLite DB written to {db_path}")
