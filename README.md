# Bank Transaction Analytics

SQL-driven analytics project on a synthetic banking dataset (customers,
accounts, transactions), built to practice and demonstrate the exact SQL
skills used in a retail/business analytics role: joins, CTEs, window
functions, aggregations, and data cleaning.

## Why synthetic data

Real banking transaction data isn't publicly available for privacy
reasons, so this project generates a realistic synthetic dataset
(400 customers, ~470 accounts, ~20,000 transactions) with deliberately
injected data-quality issues -- null categories, duplicate rows,
inconsistent casing/whitespace -- so the SQL has genuine cleaning work
to do rather than working on already-tidy data.

## Project structure

```
bank-transaction-analytics/
├── data/
│   ├── customers.csv, accounts.csv, transactions.csv   (raw, uncleaned)
│   └── bank.db                                          (SQLite database)
├── sql/
│   └── analysis.sql          -- all analysis queries, documented inline
├── scripts/
│   ├── generate_data.py      -- builds the synthetic dataset
│   └── run_analysis.py       -- runs analysis.sql, exports CSVs + charts
└── output/
    ├── *.csv                 -- one CSV per query result
    └── *.png                 -- summary charts
```

## What's demonstrated

**Data quality / cleaning**
- Detecting NULL values and exact-duplicate rows
- Normalizing inconsistent category text (casing, whitespace)
- A `transactions_clean` SQL VIEW that dedupes using `ROW_NUMBER()`
  and standardizes categories -- so downstream queries never touch
  raw dirty data directly

**Joins**
- Three-table join (`customers` → `accounts` → `transactions_clean`)
  to build a per-customer spend summary

**CTEs**
- Monthly spend-by-category aggregation built as a CTE, reused across
  two downstream queries

**Window functions**
- `LAG()` for month-over-month spend change per category
- Running total via `SUM() OVER (... ROWS BETWEEN UNBOUNDED PRECEDING ...)`
- `RANK()` to rank customers by spend within their segment

**Aggregation / business reporting**
- City-level portfolio summary (customers, accounts, avg transaction,
  total spend) -- the kind of rollup a stakeholder would ask for

**Basic anomaly detection**
- Z-score style outlier flagging per category, as a lightweight stand-in
  for "identify inconsistencies/anomalies" in a real analyst workflow

## How to run

```bash
pip install pandas numpy matplotlib
python scripts/generate_data.py     # builds data/bank.db
python scripts/run_analysis.py      # runs sql/analysis.sql, writes output/
```

## Key findings (from the synthetic data)

- Total monthly spend fluctuates in the ~1.33M-1.60M INR range across
  the observed period, with no strong single trend -- see
  `output/chart_monthly_spend_trend.png`.
- Groceries and Shopping are consistently the largest spend categories.
- A small number of transactions (~25) were flagged as statistical
  outliers (|z-score| > 3) within their category, worth a manual review
  in a real deployment.

## Notes

This is a portfolio/practice project using generated data, built to
demonstrate SQL and data-analysis technique -- not a production system
or real financial data.
