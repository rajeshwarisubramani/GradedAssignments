# Retail Analysis

This project analyzes `data/sample transaction.csv` using Pandas, Matplotlib, and Seaborn.

## What the script does

- Loads and inspects the transaction dataset (columns, dtypes, missing values, numeric summary)
- Cleans key fields (`Date`, `Total_Items`, `Total_Cost`, `Discount_Applied`)
- Finds patterns in city activity, payment behavior, monthly revenue, promotions, and customer categories
- Detects high-value transaction anomalies with the IQR method
- Produces clear plots and one-line observations
- Writes a final findings document

## Run

```powershell
python -m pip install -r requirements.txt
python main.py
```

## Assignment Task Script

Run the assignment-focused pipeline (Tasks 1-6):

```powershell
python analysis.py
```

## Task 1 & Task 2: Data Preparation & Basic Exploration

Run the comprehensive data preparation and basic exploration script:

```powershell
python data/basicExploration.py
```

**Task 1 - Data Preparation:**
- Reads CSV file
- Parses and converts Date column to datetime format
- Extracts temporal features (Year, Month, MonthName, DayOfWeek, Quarter)
- Cleans and preprocesses data (numeric conversion, boolean normalization, NaN removal)

**Task 2 - Basic Exploration:**
- Total transactions: 2,099
- Unique customers: 2,061
- Top 5 products identified
- Top cities by transaction count ranked

**Generated Outputs:**
- Task 1 Plots: `task1_transactions_by_*.png` (year, month, dayofweek, quarter)
- Task 2 Plots: `task2_*` (summary, top 5 products, top cities, cities pie chart)
- Report: `task1_task2_exploration_report.md`

Optional smoke test (checks that key CSV/plot artifacts are created):

```powershell
python smoke_test_analysis.py
```

## Outputs

After running, artifacts are saved to `outputs/`:

- `columns_and_dtypes.csv`
- `missing_values.csv`
- `numeric_summary.csv`
- `city_transactions.csv`
- `payment_distribution.csv`
- `monthly_revenue.csv`
- `store_type_revenue.csv`
- `store_discount_performance.csv`
- `store_type_season_revenue.csv`
- `promotion_performance.csv`
- `category_spend.csv`
- `seasonality.csv`
- `anomalies.csv`
- `insights.md`
- `plots/transactions_by_city.png`
- `plots/payment_distribution.png`
- `plots/monthly_revenue_trend.png`
- `plots/revenue_by_store_type.png`
- `plots/store_discount_revenue_by_store_type.png`
- `plots/storetype_discount_scatter.png`
- `plots/promotion_store_type_scatter.png`
- `plots/revenue_by_store_type_and_season.png`

