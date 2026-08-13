"""
Runs the SQL analysis against the SQLite DB, exports each query's results
as a CSV into output/, and generates a couple of summary charts.
"""
import sqlite3
import re
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "bank.db"
SQL_FILE = ROOT / "sql" / "analysis.sql"
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

sql_text = SQL_FILE.read_text()

# split into individual statements on ';' at end of line, skipping comments
def split_statements(text):
    # strip line comments
    lines = [l for l in text.splitlines() if not l.strip().startswith("--")]
    text = "\n".join(lines)
    stmts = [s.strip() for s in text.split(";") if s.strip()]
    return stmts

statements = split_statements(sql_text)

conn = sqlite3.connect(DB)

named_queries = {
    0: "data_quality_null_categories",
    1: "data_quality_duplicates",
    2: "data_quality_distinct_categories",
    # 3 = DROP VIEW, 4 = CREATE VIEW (handled separately, not SELECTs)
    5: "customer_spend_summary_join",
    6: "monthly_category_spend_cte",
    7: "monthly_category_window_functions",
    8: "customer_rank_by_segment_window",
    9: "city_portfolio_summary",
    10: "anomaly_detection_zscore",
}

results = {}
i = 0
for stmt in statements:
    upper = stmt.strip().upper()
    if upper.startswith("DROP VIEW") or upper.startswith("CREATE VIEW"):
        conn.execute(stmt)
        conn.commit()
        i += 1
        continue
    if upper.startswith("SELECT") or upper.startswith("WITH"):
        try:
            df = pd.read_sql_query(stmt, conn)
            name = named_queries.get(i, f"query_{i}")
            results[name] = df
            df.to_csv(OUT / f"{name}.csv", index=False)
            print(f"[{name}] {len(df)} rows -> output/{name}.csv")
        except Exception as e:
            print(f"Query {i} failed: {e}")
        i += 1
        continue
    i += 1

conn.close()

# ---------------- Charts ----------------
# Chart 1: monthly total spend trend
mc = results.get("monthly_category_spend_cte")
if mc is not None and not mc.empty:
    monthly_total = mc.groupby("month", as_index=False)["spend"].sum()
    plt.figure(figsize=(8, 4.5))
    plt.plot(monthly_total["month"], monthly_total["spend"], marker="o")
    plt.xticks(rotation=45, ha="right")
    plt.title("Total Monthly Spend")
    plt.ylabel("Spend (INR)")
    plt.tight_layout()
    plt.savefig(OUT / "chart_monthly_spend_trend.png", dpi=140)
    plt.close()

# Chart 2: spend by category (bar)
if mc is not None and not mc.empty:
    cat_total = mc.groupby("category", as_index=False)["spend"].sum().sort_values("spend", ascending=False)
    plt.figure(figsize=(8, 4.5))
    plt.bar(cat_total["category"], cat_total["spend"], color="#2c6e91")
    plt.xticks(rotation=45, ha="right")
    plt.title("Total Spend by Category")
    plt.ylabel("Spend (INR)")
    plt.tight_layout()
    plt.savefig(OUT / "chart_spend_by_category.png", dpi=140)
    plt.close()

# Chart 3: city portfolio spend
city_df = results.get("city_portfolio_summary")
if city_df is not None and not city_df.empty:
    plt.figure(figsize=(8, 4.5))
    plt.bar(city_df["city"], city_df["total_spend"], color="#8a3b3b")
    plt.xticks(rotation=45, ha="right")
    plt.title("Total Spend by City")
    plt.ylabel("Spend (INR)")
    plt.tight_layout()
    plt.savefig(OUT / "chart_spend_by_city.png", dpi=140)
    plt.close()

print("\nDone. CSVs and charts written to output/.")
