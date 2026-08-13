-- ============================================================================
-- Bank Transaction Analytics -- SQL Analysis
-- Dataset: customers, accounts, transactions (SQLite)
-- Demonstrates: joins, CTEs, window functions, aggregations, data cleaning
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 0. DATA QUALITY CHECKS
-- Raw data has: NULL categories (~150 rows), a small number of exact
-- duplicate transaction rows, and inconsistent category casing/whitespace.
-- ----------------------------------------------------------------------------

-- 0a. Count NULL categories
SELECT COUNT(*) AS null_category_rows
FROM transactions
WHERE category IS NULL;

-- 0b. Find duplicate transaction rows (same account, date, category, amount)
SELECT account_id, txn_date, category, amount, COUNT(*) AS n
FROM transactions
GROUP BY account_id, txn_date, category, amount
HAVING COUNT(*) > 1;

-- 0c. Inspect inconsistent category casing/whitespace
SELECT DISTINCT category
FROM transactions
ORDER BY category;

-- ----------------------------------------------------------------------------
-- 1. CLEAN VIEW
-- Normalizes category casing/whitespace, drops exact-duplicate rows via
-- ROW_NUMBER() window function, and fills unknown categories.
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS transactions_clean;
CREATE VIEW transactions_clean AS
WITH deduped AS (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY account_id, txn_date, category, amount
               ORDER BY transaction_id
           ) AS rn
    FROM transactions
)
SELECT
    transaction_id,
    account_id,
    txn_date,
    COALESCE(TRIM(LOWER(category)), 'unknown') AS category,
    amount
FROM deduped
WHERE rn = 1;


-- ----------------------------------------------------------------------------
-- 2. JOIN -- customer-level spend summary
-- Joins customers -> accounts -> transactions_clean
-- ----------------------------------------------------------------------------
SELECT
    c.customer_id,
    c.segment,
    c.city,
    COUNT(t.transaction_id)                       AS txn_count,
    ROUND(SUM(CASE WHEN t.amount < 0 THEN -t.amount ELSE 0 END), 2) AS total_spend,
    ROUND(SUM(CASE WHEN t.amount > 0 THEN t.amount ELSE 0 END), 2)  AS total_credits
FROM customers c
JOIN accounts a ON a.customer_id = c.customer_id
JOIN transactions_clean t ON t.account_id = a.account_id
GROUP BY c.customer_id, c.segment, c.city
ORDER BY total_spend DESC
LIMIT 20;


-- ----------------------------------------------------------------------------
-- 3. CTE + AGGREGATION -- monthly spend by category
-- ----------------------------------------------------------------------------
WITH monthly_category_spend AS (
    SELECT
        strftime('%Y-%m', txn_date) AS month,
        category,
        SUM(-amount) AS spend
    FROM transactions_clean
    WHERE amount < 0
    GROUP BY month, category
)
SELECT month, category, ROUND(spend, 2) AS spend
FROM monthly_category_spend
ORDER BY month, spend DESC;


-- ----------------------------------------------------------------------------
-- 4. WINDOW FUNCTIONS -- month-over-month spend change per category,
--    and running total of spend per category over time.
-- ----------------------------------------------------------------------------
WITH monthly_category_spend AS (
    SELECT
        strftime('%Y-%m', txn_date) AS month,
        category,
        SUM(-amount) AS spend
    FROM transactions_clean
    WHERE amount < 0
    GROUP BY month, category
)
SELECT
    month,
    category,
    ROUND(spend, 2) AS spend,
    ROUND(LAG(spend) OVER (PARTITION BY category ORDER BY month), 2) AS prev_month_spend,
    ROUND(
        spend - LAG(spend) OVER (PARTITION BY category ORDER BY month), 2
    ) AS mom_change,
    ROUND(
        SUM(spend) OVER (PARTITION BY category ORDER BY month
                          ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2
    ) AS running_total
FROM monthly_category_spend
ORDER BY category, month;


-- ----------------------------------------------------------------------------
-- 5. WINDOW FUNCTION -- rank customers by spend within their segment
-- ----------------------------------------------------------------------------
WITH customer_spend AS (
    SELECT
        c.customer_id,
        c.segment,
        ROUND(SUM(-t.amount), 2) AS total_spend
    FROM customers c
    JOIN accounts a ON a.customer_id = c.customer_id
    JOIN transactions_clean t ON t.account_id = a.account_id
    WHERE t.amount < 0
    GROUP BY c.customer_id, c.segment
)
SELECT
    customer_id,
    segment,
    total_spend,
    RANK() OVER (PARTITION BY segment ORDER BY total_spend DESC) AS spend_rank_in_segment
FROM customer_spend
ORDER BY segment, spend_rank_in_segment
LIMIT 30;


-- ----------------------------------------------------------------------------
-- 6. AGGREGATION -- city-level portfolio summary (business-facing report)
-- ----------------------------------------------------------------------------
SELECT
    c.city,
    COUNT(DISTINCT c.customer_id)                AS customers,
    COUNT(DISTINCT a.account_id)                 AS accounts,
    ROUND(AVG(t.amount), 2)                      AS avg_txn_amount,
    ROUND(SUM(CASE WHEN t.amount < 0 THEN -t.amount ELSE 0 END), 2) AS total_spend
FROM customers c
JOIN accounts a ON a.customer_id = c.customer_id
JOIN transactions_clean t ON t.account_id = a.account_id
GROUP BY c.city
ORDER BY total_spend DESC;


-- ----------------------------------------------------------------------------
-- 7. ANOMALY FLAGGING -- simple z-score style outlier detection per category
-- (flags transactions whose amount is far from that category's mean --
--  a lightweight stand-in for the "identify inconsistencies/anomalies"
--  requirement in the JD)
-- ----------------------------------------------------------------------------
WITH stats AS (
    SELECT
        category,
        AVG(amount) AS mean_amt,
        -- SQLite has no STDDEV built-in; approximate via AVG of squared diffs
        (AVG(amount * amount) - AVG(amount) * AVG(amount)) AS variance
    FROM transactions_clean
    GROUP BY category
)
SELECT
    t.transaction_id,
    t.account_id,
    t.category,
    t.amount,
    ROUND(s.mean_amt, 2) AS category_mean,
    ROUND((t.amount - s.mean_amt) / NULLIF(SQRT(s.variance), 0), 2) AS z_score
FROM transactions_clean t
JOIN stats s ON s.category = t.category
WHERE ABS((t.amount - s.mean_amt) / NULLIF(SQRT(s.variance), 0)) > 3
ORDER BY ABS((t.amount - s.mean_amt) / NULLIF(SQRT(s.variance), 0)) DESC
LIMIT 25;
