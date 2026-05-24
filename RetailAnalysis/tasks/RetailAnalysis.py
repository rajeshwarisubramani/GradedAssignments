"""
=============================================================
  RETAIL ANALYSIS — COMPLETE MERGED SCRIPT
  ─────────────────────────────────────────
  Sources merged:
    • analysis.py          (Tasks 1-6: data prep → dashboard)
    • analyse.py           (Customer Behaviour: spending + store-type)
    • discountevaluation.py(Discount/Promotion evaluation + seasonality)

  Sections:
    1.  Data Preparation & Cleaning
    2.  Basic Exploration
    3.  Customer Behaviour — Spending Patterns
    4.  Customer Behaviour — Store-Type Preferences
    5.  Discount vs Non-Discount Analysis
    6.  Promotion Effectiveness
    7.  Seasonal Trends & Preferences
    8.  Visualisations
          8a. Behaviour Plots   → outputs/behaviour_plots/  (8 plots)
          8b. Discount Plots    → outputs/discount_plots/   (9 plots)
          8c. Summary Dashboard → outputs/plots/            (1 plot)
    9.  Comprehensive Key Insights Summary
=============================================================
"""

# ── Standard-library imports ──────────────────────────────────────────────────
from pathlib import Path
import ast
import warnings
warnings.filterwarnings("ignore")

# ── Third-party imports ───────────────────────────────────────────────────────
import pandas as pd
import numpy as np
from scipy import stats                  # Welch's t-test for discount significance
import matplotlib
matplotlib.use("Agg")                    # non-interactive backend, no display needed
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.gridspec import GridSpec
import seaborn as sns


# =============================================================================
#  PATHS & OUTPUT DIRECTORIES
# =============================================================================
BASE_DIR      = Path(__file__).resolve().parent   # tasks/
PROJECT_ROOT  = BASE_DIR.parent                   # RetailAnalysis/
DATA_FILE     = PROJECT_ROOT / "data" / "Retail_Transactions_Dataset-1.csv"

# Three separate output folders — created automatically if they don't exist
BEHAVIOUR_DIR = PROJECT_ROOT / "outputs" / "behaviour_plots"
DISCOUNT_DIR  = PROJECT_ROOT / "outputs" / "discount_plots"
DASHBOARD_DIR = PROJECT_ROOT / "outputs" / "plots"

for d in (BEHAVIOUR_DIR, DISCOUNT_DIR, DASHBOARD_DIR):
    d.mkdir(parents=True, exist_ok=True)


# =============================================================================
#  SHARED VISUAL STYLE
# =============================================================================
PALETTE = "Set2"
FIG_DPI = 150
sns.set_theme(style="whitegrid", palette=PALETTE)
plt.rcParams.update({"axes.titlesize": 13, "axes.labelsize": 11,
                     "figure.dpi": FIG_DPI})
COLORS       = sns.color_palette(PALETTE, 12)   # 12 distinct colours
SEASON_ORDER = ["Spring", "Summer", "Fall", "Winter"]
DOW_ORDER    = ["Monday", "Tuesday", "Wednesday", "Thursday",
                "Friday", "Saturday", "Sunday"]


# =============================================================================
#  SECTION 1 — DATA PREPARATION & CLEANING
# =============================================================================
print("\n" + "=" * 60)
print("  SECTION 1 — DATA PREPARATION & CLEANING")
print("=" * 60)

# ── 1a. Load the CSV (utf-8-sig handles optional BOM character) ───────────────
df = pd.read_csv(DATA_FILE, encoding="utf-8-sig")
print(f"\nRaw shape  : {df.shape[0]:,} rows × {df.shape[1]} columns")
print(f"Columns    : {list(df.columns)}")
print(f"\nColumn dtypes (before cleaning):\n{df.dtypes}")

# ── 1b. Parse the Date column — handles mixed DD-MM-YYYY / YYYY-MM-DD formats ─
df["Date"] = pd.to_datetime(
    df["Date"], format="mixed", dayfirst=True, errors="coerce"
)
bad_dates = df["Date"].isna().sum()
if bad_dates:
    print(f"\n⚠  Warning: {bad_dates} rows with unparseable dates → set to NaT.")

# ── 1c. Extract all temporal features needed downstream ───────────────────────
df["Year"]      = df["Date"].dt.year
df["Month"]     = df["Date"].dt.month
df["MonthName"] = df["Date"].dt.strftime("%b")
df["DayOfWeek"] = df["Date"].dt.day_name()
df["Quarter"]   = df["Date"].dt.quarter

# ── 1d. Normalise Discount_Applied string → Python bool ───────────────────────
df["Discount_Applied"] = (
    df["Discount_Applied"]
    .astype(str).str.strip().str.upper()
    .map({"TRUE": True, "FALSE": False})
)

# ── 1e. Clean the Promotion column (fill NaN → "None") ────────────────────────
df["Promotion"] = df["Promotion"].fillna("None").str.strip()

# ── 1f. Parse the Product column (stored as a stringified Python list) ────────
def parse_products(raw):
    """Convert string repr of list  e.g. "['Milk','Bread']"  →  ['Milk', 'Bread']."""
    try:
        return ast.literal_eval(str(raw))
    except Exception:
        return []

df["Product_List"] = df["Product"].apply(parse_products)

# ── 1g. Sanity check after cleaning ───────────────────────────────────────────
print(f"\nMissing values per column after cleaning:\n{df.isnull().sum()}")
print(f"\nDate range : {df['Date'].min().date()} → {df['Date'].max().date()}")
print(f"\nSample of cleaned data:")
print(df[["Transaction_ID", "Date", "Year", "Month", "DayOfWeek",
          "Total_Cost", "Discount_Applied", "Promotion"]].head(3).to_string(index=False))


# =============================================================================
#  SECTION 2 — BASIC EXPLORATION
# =============================================================================
print("\n" + "=" * 60)
print("  SECTION 2 — BASIC EXPLORATION")
print("=" * 60)

# 2a. Total transactions and unique customers
total_txn        = len(df)
unique_customers = df["Customer_Name"].nunique()
print(f"\n• Total transactions : {total_txn:,}")
print(f"• Unique customers   : {unique_customers:,}")
print(f"• Cities covered     : {df['City'].nunique()}")
print(f"• Store types        : {sorted(df['Store_Type'].unique())}")
print(f"• Seasons present    : {sorted(df['Season'].unique())}")
print(f"• Promotions present : {sorted(df['Promotion'].unique())}")

# 2b. Top-5 most common products (flatten nested Product_List)
all_products   = [p for sublist in df["Product_List"] for p in sublist]
top5_products  = pd.Series(all_products).value_counts().head(5)
print("\n• Top-5 most common products:")
print(top5_products.to_string())

# 2c. Cities with the highest transaction counts
top_cities = df["City"].value_counts().head(10)
print("\n• Transaction count by city (top 10):")
print(top_cities.to_string())


# =============================================================================
#  SECTION 3 — CUSTOMER BEHAVIOUR: SPENDING PATTERNS
# =============================================================================
print("\n" + "=" * 60)
print("  SECTION 3 — CUSTOMER BEHAVIOUR: SPENDING PATTERNS")
print("=" * 60)

# ── 3A1. Descriptive spend statistics per Customer Category ───────────────────
# Shows mean, median, spread, and extremes to compare categories fairly.
spend_stats = (
    df.groupby("Customer_Category")["Total_Cost"]
    .agg(
        Transactions = "count",
        Mean         = "mean",
        Median       = "median",
        Std          = "std",
        Min          = "min",
        Max          = "max",
    )
    .round(2)
    .sort_values("Mean", ascending=False)
)
print("\n3A1. Spend statistics by Customer Category:")
print(spend_stats.to_string())

# Average spend per category (simple series for quick lookups later)
avg_spend_cat = spend_stats["Mean"]

# ── 3A2. Customer spend segmentation — Low / Mid / High ──────────────────────
# Compute each customer's TOTAL lifetime spend, then bin into 3 equal-width bands.
cust_total   = df.groupby("Customer_Name")["Total_Cost"].sum()
seg_labels   = ["Low Spender", "Mid Spender", "High Spender"]
cust_segment = pd.cut(cust_total, bins=3, labels=seg_labels)

segment_counts = cust_segment.value_counts().reindex(seg_labels)
print("\n3A2. Customer spend segments (by total lifetime spend):")
print(segment_counts.to_string())

# Attach segment label to every transaction row for downstream use
df = df.merge(
    cust_segment.rename("Spend_Segment").reset_index(),
    on="Customer_Name", how="left"
)

# ── 3A3. Average spend by Day of Week ────────────────────────────────────────
# Reveals whether weekends or specific weekdays drive higher basket values.
dow_spend = (
    df.groupby("DayOfWeek")["Total_Cost"]
    .mean()
    .reindex(DOW_ORDER)
    .round(2)
)
print("\n3A3. Average spend by Day of Week:")
print(dow_spend.to_string())
print(f"  ➜ Peak day    : {dow_spend.idxmax()}  (${dow_spend.max():.2f} avg)")
print(f"  ➜ Quietest day: {dow_spend.idxmin()} (${dow_spend.min():.2f} avg)")

# ── 3A4. Average spend & volume by Payment Method ────────────────────────────
# Identifies whether digital payment users spend differently from cash users.
pay_spend = (
    df.groupby("Payment_Method")["Total_Cost"]
    .agg(Avg_Spend="mean", Transactions="count")
    .round(2)
    .sort_values("Avg_Spend", ascending=False)
)
print("\n3A4. Avg spend & volume by Payment Method:")
print(pay_spend.to_string())
print(f"  ➜ Highest avg-spend method : {pay_spend['Avg_Spend'].idxmax()} "
      f"(${pay_spend['Avg_Spend'].max():.2f})")
print(f"  ➜ Most-used payment method : {pay_spend['Transactions'].idxmax()} "
      f"({pay_spend['Transactions'].max():,} txns)")

# Payment method preference per customer category (cross-tabulation)
pay_pref_pivot = (
    df.groupby(["Customer_Category", "Payment_Method"])
    .size()
    .unstack(fill_value=0)
)
print("\n  Payment method counts per customer category:")
print(pay_pref_pivot.to_string())

# ── 3A5. Average basket size (items) per Customer Category ───────────────────
# Larger baskets don't always mean higher spend — this cross-checks 3A1.
basket = (
    df.groupby("Customer_Category")["Total_Items"]
    .mean()
    .round(2)
    .sort_values(ascending=False)
)
print("\n3A5. Average basket size (items) by Customer Category:")
print(basket.to_string())
print(f"  ➜ Largest basket  : {basket.idxmax()} ({basket.max():.2f} items/txn)")
print(f"  ➜ Smallest basket : {basket.idxmin()} ({basket.min():.2f} items/txn)")

# Average items per transaction by store type
avg_items_store = (
    df.groupby("Store_Type")["Total_Items"]
    .mean()
    .sort_values(ascending=False)
    .round(2)
)
print("\n  Avg items per transaction by store type:")
print(avg_items_store.to_string())

# ── 3A6. Correlation — Total_Items vs Total_Cost ─────────────────────────────
# Pearson r tells us whether buying more items always means spending more.
corr_val = df[["Total_Items", "Total_Cost"]].corr().loc["Total_Items", "Total_Cost"]
print(f"\n3A6. Pearson correlation — Total_Items vs Total_Cost : {corr_val:.4f}")
if abs(corr_val) > 0.5:
    print("  ➜ Strong relationship: more items strongly predict higher spend.")
elif abs(corr_val) > 0.2:
    print("  ➜ Moderate relationship between items purchased and spend.")
else:
    print("  ➜ Weak relationship — spend is largely independent of item count.")

# ── 3A7. Repeat-visit frequency per customer ─────────────────────────────────
# Counts how many transactions each customer made; summarises by category.
visit_freq = df.groupby("Customer_Name")["Transaction_ID"].count().rename("Visit_Count")
df = df.merge(visit_freq.reset_index(), on="Customer_Name", how="left")

freq_by_cat = (
    df.drop_duplicates("Customer_Name")        # one row per customer
    .groupby("Customer_Category")["Visit_Count"]
    .agg(Avg_Visits="mean", Max_Visits="max")
    .round(2)
    .sort_values("Avg_Visits", ascending=False)
)
print("\n3A7. Repeat-visit frequency per Customer Category:")
print(freq_by_cat.to_string())
print(f"  ➜ Most loyal category : {freq_by_cat['Avg_Visits'].idxmax()} "
      f"({freq_by_cat['Avg_Visits'].max():.2f} avg visits)")


# =============================================================================
#  SECTION 4 — CUSTOMER BEHAVIOUR: STORE-TYPE PREFERENCES
# =============================================================================
print("\n" + "=" * 60)
print("  SECTION 4 — CUSTOMER BEHAVIOUR: STORE-TYPE PREFERENCES")
print("=" * 60)

# ── 4B1. Overall volume, avg spend & revenue per store type ──────────────────
store_vol = (
    df.groupby("Store_Type")
    .agg(
        Transactions  = ("Transaction_ID", "count"),
        Avg_Spend     = ("Total_Cost",      "mean"),
        Total_Revenue = ("Total_Cost",      "sum"),
    )
    .round(2)
    .sort_values("Transactions", ascending=False)
)
print("\n4B1. Store Type — Volume, Avg Spend, Total Revenue:")
print(store_vol.to_string())
print(f"  ➜ Most visited store    : {store_vol['Transactions'].idxmax()} "
      f"({store_vol['Transactions'].max():,} visits)")
print(f"  ➜ Highest avg spend     : {store_vol['Avg_Spend'].idxmax()} "
      f"(${store_vol['Avg_Spend'].max():.2f})")
print(f"  ➜ Highest total revenue : {store_vol['Total_Revenue'].idxmax()} "
      f"(${store_vol['Total_Revenue'].max():,.2f})")

# ── 4B2. Customer Category × Store Type — transaction count (heatmap data) ───
# Cross-tabulation reveals which customer segments shop where most frequently.
cat_store_count = pd.crosstab(df["Customer_Category"], df["Store_Type"])
print("\n4B2. Customer Category × Store Type (transaction count):")
print(cat_store_count.to_string())

pref_store = cat_store_count.idxmax(axis=1)   # preferred store per category
print("\n  ➜ Most preferred store per Customer Category:")
for cat, store in pref_store.items():
    count = cat_store_count.loc[cat, store]
    print(f"     {cat:15s} → {store}  ({count:,} visits)")

# ── 4B3. Customer Category × Store Type — average spend ──────────────────────
# Highlights premium vs budget shopping behaviour per segment per store type.
cat_store_spend = (
    df.groupby(["Customer_Category", "Store_Type"])["Total_Cost"]
    .mean()
    .unstack()
    .round(2)
)
print("\n4B3. Avg spend — Customer Category × Store Type:")
print(cat_store_spend.to_string())

# ── 4B4. Most preferred store type per city ──────────────────────────────────
city_store       = pd.crosstab(df["City"], df["Store_Type"])
pref_store_city  = city_store.idxmax(axis=1)
print("\n4B4. Most preferred store type by City:")
for city, store in pref_store_city.items():
    print(f"     {city:15s} → {store}")

# ── 4B5. Discount usage rate per store type ───────────────────────────────────
# Fraction of transactions with Discount_Applied == True, expressed as %.
store_discount = (
    df.groupby("Store_Type")["Discount_Applied"]
    .mean()
    .mul(100).round(1)
    .sort_values(ascending=False)
    .rename("Discount_Rate_%")
)
print("\n4B5. Discount usage rate (%) by Store Type:")
print(store_discount.to_string())
print(f"  ➜ Highest discount rate: {store_discount.idxmax()} "
      f"({store_discount.max():.1f}%)")
print(f"  ➜ Lowest  discount rate: {store_discount.idxmin()} "
      f"({store_discount.min():.1f}%)")

# ── 4B6. Store Type × Season transaction count ───────────────────────────────
# Shows whether certain stores are seasonally busier than others.
# store_season: rows = Store_Type, cols = Season
store_season = (
    df.groupby(["Store_Type", "Season"])
    .size()
    .unstack(fill_value=0)
    .reindex(columns=SEASON_ORDER)
)
print("\n4B6. Transaction count — Store Type × Season:")
print(store_season.to_string())

# ── 4B7. Preferred payment method per store type ─────────────────────────────
# Tells us whether contactless/digital payment adoption varies by store format.
store_pay      = pd.crosstab(df["Store_Type"], df["Payment_Method"])
pref_pay_store = store_pay.idxmax(axis=1)
print("\n4B7. Most-used payment method by Store Type:")
for store, pay in pref_pay_store.items():
    count = store_pay.loc[store, pay]
    print(f"     {store:20s} → {pay}  ({count:,} transactions)")


# =============================================================================
#  SECTION 5 — DISCOUNT vs NON-DISCOUNT ANALYSIS
# =============================================================================
print("\n" + "=" * 60)
print("  SECTION 5 — DISCOUNT vs NON-DISCOUNT ANALYSIS")
print("=" * 60)

# Convenience boolean masks used throughout this section
disc    = df["Discount_Applied"] == True
no_disc = df["Discount_Applied"] == False

# ── 5A1. Volume & percentage split ────────────────────────────────────────────
disc_count    = disc.sum()
no_disc_count = no_disc.sum()
total         = len(df)

print(f"\n5A1. Transaction Volume Split:")
print(f"  Discount Applied   : {disc_count:,}  ({disc_count/total*100:.1f}%)")
print(f"  No Discount        : {no_disc_count:,}  ({no_disc_count/total*100:.1f}%)")
print(f"  Total Transactions : {total:,}")

# ── 5A2. KPI comparison — Discounted vs Non-Discounted ───────────────────────
# Compares avg spend, median spend, total revenue, and avg items side-by-side.
compare = (
    df.groupby("Discount_Applied")
    .agg(
        Transactions  = ("Transaction_ID", "count"),
        Avg_Spend     = ("Total_Cost",      "mean"),
        Median_Spend  = ("Total_Cost",      "median"),
        Total_Revenue = ("Total_Cost",      "sum"),
        Avg_Items     = ("Total_Items",     "mean"),
    )
    .round(2)
)
compare.index = compare.index.map({True: "Discount Applied", False: "No Discount"})
print("\n5A2. KPI Comparison — Discounted vs Non-Discounted:")
print(compare.to_string())

rev_lift   = (compare.loc["Discount Applied", "Total_Revenue"]
              - compare.loc["No Discount",    "Total_Revenue"])
spend_diff = (compare.loc["Discount Applied", "Avg_Spend"]
              - compare.loc["No Discount",    "Avg_Spend"])
print(f"\n  ➜ Revenue difference   : ${rev_lift:+,.2f}  "
      f"({'discounted earns more' if rev_lift > 0 else 'no-discount earns more'})")
print(f"  ➜ Avg spend difference : ${spend_diff:+.2f} per transaction")

# Also build a simplified disc_avg alias used in the dashboard plot
disc_avg = compare[["Avg_Spend", "Transactions"]].rename(
    columns={"Avg_Spend": "Avg_Cost"}
)

# ── 5A3. Discount uptake rate by Customer Category ────────────────────────────
# Shows which customer segments use discounts most often.
cat_disc = (
    df.groupby("Customer_Category")["Discount_Applied"]
    .mean()
    .mul(100).round(1)
    .sort_values(ascending=False)
    .rename("Discount_Rate_%")
)
print("\n5A3. Discount uptake rate (%) by Customer Category:")
print(cat_disc.to_string())
print(f"  ➜ Highest discount users: {cat_disc.idxmax()} ({cat_disc.max():.1f}%)")
print(f"  ➜ Lowest  discount users: {cat_disc.idxmin()} ({cat_disc.min():.1f}%)")

# Avg spend WITH vs WITHOUT discount per customer category
cat_disc_spend = (
    df.groupby(["Customer_Category", "Discount_Applied"])["Total_Cost"]
    .mean()
    .unstack()
    .round(2)
)
cat_disc_spend.columns = ["No Discount", "Discount Applied"]
print("\n  Avg spend with vs without discount per Customer Category:")
print(cat_disc_spend.to_string())

# ── 5A4. Discount uptake rate by Store Type ───────────────────────────────────
store_disc = (
    df.groupby("Store_Type")["Discount_Applied"]
    .mean()
    .mul(100).round(1)
    .sort_values(ascending=False)
    .rename("Discount_Rate_%")
)
print("\n5A4. Discount uptake rate (%) by Store Type:")
print(store_disc.to_string())
print(f"  ➜ Highest: {store_disc.idxmax()} ({store_disc.max():.1f}%)  "
      f"| Lowest: {store_disc.idxmin()} ({store_disc.min():.1f}%)")

# ── 5A5. Discount uptake rate by Season ───────────────────────────────────────
season_disc = (
    df.groupby("Season")["Discount_Applied"]
    .mean()
    .mul(100).round(1)
    .reindex(SEASON_ORDER)
    .rename("Discount_Rate_%")
)
print("\n5A5. Discount uptake rate (%) by Season:")
print(season_disc.to_string())
print(f"  ➜ Peak discount season: {season_disc.idxmax()} ({season_disc.max():.1f}%)")

# ── 5A6. Discount uptake rate by Payment Method ───────────────────────────────
pay_disc = (
    df.groupby("Payment_Method")["Discount_Applied"]
    .mean()
    .mul(100).round(1)
    .sort_values(ascending=False)
    .rename("Discount_Rate_%")
)
print("\n5A6. Discount uptake rate (%) by Payment Method:")
print(pay_disc.to_string())

# ── 5A7. Statistical significance — Welch's t-test on spend ──────────────────
# Tests whether the avg-spend difference between the two groups is real.
# p < 0.05 → significant;  p ≥ 0.05 → difference may be random chance.
disc_spend_vals    = df.loc[disc,    "Total_Cost"].dropna()
no_disc_spend_vals = df.loc[no_disc, "Total_Cost"].dropna()
t_stat, p_value    = stats.ttest_ind(disc_spend_vals, no_disc_spend_vals,
                                      equal_var=False)   # Welch's t-test

print(f"\n5A7. Welch's t-test — Discounted vs Non-Discounted spend:")
print(f"  t-statistic : {t_stat:.4f}")
print(f"  p-value     : {p_value:.6f}")
if p_value < 0.05:
    print("  ➜ SIGNIFICANT — spend difference is statistically real (p < 0.05).")
else:
    print("  ➜ NOT significant — difference may be due to chance (p ≥ 0.05).")


# =============================================================================
#  SECTION 6 — PROMOTION EFFECTIVENESS
# =============================================================================
print("\n" + "=" * 60)
print("  SECTION 6 — PROMOTION EFFECTIVENESS")
print("=" * 60)

# ── 6B1. Transaction count and total revenue per promotion type ───────────────
total_rev     = df["Total_Cost"].sum()
promo_overview = (
    df.groupby("Promotion")
    .agg(
        Transactions  = ("Transaction_ID", "count"),
        Total_Revenue = ("Total_Cost",      "sum"),
    )
    .round(2)
    .sort_values("Total_Revenue", ascending=False)
)
promo_overview["Revenue_Share_%"] = (
    promo_overview["Total_Revenue"] / total_rev * 100
).round(1)
promo_overview["Txn_Share_%"] = (
    promo_overview["Transactions"] / total * 100
).round(1)
print("\n6B1. Promotion type — transactions, revenue & share:")
print(promo_overview.to_string())

# ── 6B2. Avg spend and avg items per promotion type ───────────────────────────
# A higher avg spend under a promotion = promotion drives bigger baskets.
promo_kpi = (
    df.groupby("Promotion")
    .agg(
        Avg_Spend = ("Total_Cost",  "mean"),
        Med_Spend = ("Total_Cost",  "median"),
        Avg_Items = ("Total_Items", "mean"),
    )
    .round(2)
    .sort_values("Avg_Spend", ascending=False)
)
print("\n6B2. Avg spend, median spend & avg items by Promotion Type:")
print(promo_kpi.to_string())
print(f"\n  ➜ Highest avg-spend promotion : {promo_kpi['Avg_Spend'].idxmax()} "
      f"(${promo_kpi['Avg_Spend'].max():.2f})")
print(f"  ➜ Largest basket promotion    : {promo_kpi['Avg_Items'].idxmax()} "
      f"({promo_kpi['Avg_Items'].max():.2f} items avg)")

# Also build promo_cost / promo_items aliases for the dashboard section
promo_cost  = promo_kpi["Avg_Spend"]
promo_items = promo_kpi["Avg_Items"]

# ── 6B3. Promotion uptake by Customer Category ───────────────────────────────
# Shows which promotions resonate with which customer segments.
promo_cat = pd.crosstab(df["Customer_Category"], df["Promotion"])
print("\n6B3. Promotion type × Customer Category (transaction count):")
print(promo_cat.to_string())

best_promo_per_cat = promo_cat.idxmax(axis=1)
print("\n  ➜ Most-used promotion per Customer Category:")
for cat, promo in best_promo_per_cat.items():
    print(f"     {cat:15s} → {promo}  ({promo_cat.loc[cat, promo]:,} txns)")

# ── 6B4. Promotion usage by Store Type ───────────────────────────────────────
promo_store         = pd.crosstab(df["Store_Type"], df["Promotion"])
best_promo_per_store = promo_store.idxmax(axis=1)
print("\n6B4. Promotion type × Store Type (transaction count):")
print(promo_store.to_string())
print("\n  ➜ Most-used promotion per Store Type:")
for store, promo in best_promo_per_store.items():
    print(f"     {store:20s} → {promo}  ({promo_store.loc[store, promo]:,} txns)")

# ── 6B5. Promotion revenue share per Season ──────────────────────────────────
promo_season_rev = (
    df.groupby(["Season", "Promotion"])["Total_Cost"]
    .sum()
    .unstack(fill_value=0)
    .reindex(SEASON_ORDER)
    .round(2)
)
# Express each row as % of seasonal total for fair cross-season comparison
promo_season_pct = (
    promo_season_rev
    .div(promo_season_rev.sum(axis=1), axis=0)
    .mul(100).round(1)
)
print("\n6B5. Promotion revenue share (%) by Season:")
print(promo_season_pct.to_string())

# ── 6B6. Best-performing promotion per Customer Category (by avg spend) ───────
best_promo_spend = (
    df.groupby(["Customer_Category", "Promotion"])["Total_Cost"]
    .mean()
    .unstack()
    .round(2)
)
print("\n6B6. Avg spend per Customer Category × Promotion Type:")
print(best_promo_spend.to_string())
print("\n  ➜ Best promotion (highest avg spend) per Customer Category:")
for cat in best_promo_spend.index:
    best = best_promo_spend.loc[cat].idxmax()
    val  = best_promo_spend.loc[cat].max()
    print(f"     {cat:15s} → {best}  (${val:.2f} avg)")


# =============================================================================
#  SECTION 7 — SEASONAL TRENDS & PREFERENCES
# =============================================================================
print("\n" + "=" * 60)
print("  SECTION 7 — SEASONAL TRENDS & PREFERENCES")
print("=" * 60)

# ── 7C1. Core KPIs per season ─────────────────────────────────────────────────
season_kpi = (
    df.groupby("Season")["Total_Cost"]
    .agg(
        Transactions  = "count",
        Total_Revenue = "sum",
        Avg_Spend     = "mean",
        Med_Spend     = "median",
    )
    .round(2)
    .reindex(SEASON_ORDER)
)
print("\n7C1. Core KPIs per Season:")
print(season_kpi.to_string())
print(f"\n  ➜ Highest revenue season : {season_kpi['Total_Revenue'].idxmax()} "
      f"(${season_kpi['Total_Revenue'].max():,.2f})")
print(f"  ➜ Lowest  revenue season : {season_kpi['Total_Revenue'].idxmin()} "
      f"(${season_kpi['Total_Revenue'].min():,.2f})")
print(f"  ➜ Highest avg spend      : {season_kpi['Avg_Spend'].idxmax()} "
      f"(${season_kpi['Avg_Spend'].max():.2f})")

# Convenience aliases used in dashboard and insights
season_rev       = season_kpi["Total_Revenue"]
avg_season_spend = season_kpi["Avg_Spend"]

# ── 7C2. Season-over-season growth — annual revenue per season ────────────────
# Pivots Year × Season to show how each season's revenue changes year-on-year.
yoy = (
    df.groupby(["Year", "Season"])["Total_Cost"]
    .sum()
    .unstack()
    .reindex(columns=SEASON_ORDER)
    .round(2)
)
print("\n7C2. Annual Revenue per Season (Year × Season):")
print(yoy.to_string())

first_yr, last_yr = yoy.index.min(), yoy.index.max()
if first_yr != last_yr:
    growth = (
        (yoy.loc[last_yr] - yoy.loc[first_yr]) / yoy.loc[first_yr] * 100
    ).round(1)
    print(f"\n  Revenue growth {first_yr} → {last_yr} per season:")
    for s, g in growth.items():
        print(f"     {s:8s}: {g:+.1f}%")

# ── 7C3. Top-5 products per season ────────────────────────────────────────────
print("\n7C3. Top-5 products per Season:")
season_top_products = {}
for season in SEASON_ORDER:
    all_prods = [
        p for sublist in df.loc[df["Season"] == season, "Product_List"]
        for p in sublist
    ]
    top5 = pd.Series(all_prods).value_counts().head(5)
    season_top_products[season] = top5
    print(f"\n  {season}:")
    for prod, cnt in top5.items():
        print(f"     {prod:25s} {cnt:,} times")

# ── 7C4. Preferred store type per season ──────────────────────────────────────
# season_store: rows = Season, cols = Store_Type (transpose of store_season)
season_store = store_season.T.reindex(SEASON_ORDER)
print("\n7C4. Transaction count — Season × Store Type:")
print(season_store.to_string())

pref_store_season = season_store.idxmax(axis=1)
print("\n  ➜ Most visited store type per Season:")
for s, st in pref_store_season.items():
    print(f"     {s:8s} → {st}  ({season_store.loc[s, st]:,} visits)")

# ── 7C5. Preferred payment method per season ─────────────────────────────────
season_pay     = (
    df.groupby(["Season", "Payment_Method"])
    .size()
    .unstack(fill_value=0)
    .reindex(SEASON_ORDER)
)
pref_pay_season = season_pay.idxmax(axis=1)
print("\n7C5. Most-used payment method per Season:")
for s, pay in pref_pay_season.items():
    count = season_pay.loc[s, pay]
    print(f"     {s:8s} → {pay}  ({count:,} transactions)")

# ── 7C6. Customer category distribution per season ────────────────────────────
# Shows whether certain customer segments shop more in specific seasons.
season_cat = (
    df.groupby(["Season", "Customer_Category"])
    .size()
    .unstack(fill_value=0)
    .reindex(SEASON_ORDER)
)
print("\n7C6. Customer Category distribution per Season:")
print(season_cat.to_string())

dominant_cat_season = season_cat.idxmax(axis=1)
print("\n  ➜ Dominant Customer Category per Season:")
for s, cat in dominant_cat_season.items():
    print(f"     {s:8s} → {cat}  ({season_cat.loc[s, cat]:,} transactions)")

# ── 7C7. Promotion type dominance per season ──────────────────────────────────
season_promo = (
    df.groupby(["Season", "Promotion"])
    .size()
    .unstack(fill_value=0)
    .reindex(SEASON_ORDER)
)
dominant_promo_season = season_promo.idxmax(axis=1)
print("\n7C7. Dominant Promotion Type per Season:")
for s, promo in dominant_promo_season.items():
    cnt = season_promo.loc[s, promo]
    print(f"     {s:8s} → {promo}  ({cnt:,} transactions)")

# Revenue matrix used in the dashboard stacked bar
rev_matrix = (
    df.groupby(["Season", "Customer_Category"])["Total_Cost"]
    .sum()
    .unstack(fill_value=0)
    .reindex(SEASON_ORDER)
)


# =============================================================================
#  SECTION 8a — BEHAVIOUR PLOTS  (saved to outputs/behaviour_plots/)
# =============================================================================
print("\n" + "=" * 60)
print("  SECTION 8a — BEHAVIOUR PLOTS")
print("=" * 60)

# ── BP1: Spending Distribution by Customer Category (box plot) ────────────────
# Box plot shows median, IQR, and outliers — more informative than a simple bar.
fig, ax = plt.subplots(figsize=(12, 6))
order_cat = spend_stats.index.tolist()   # ordered high→low by mean spend
sns.boxplot(
    data=df, x="Customer_Category", y="Total_Cost",
    order=order_cat, palette=PALETTE,
    width=0.55, fliersize=3, ax=ax
)
ax.set_title("Spending Distribution by Customer Category", fontweight="bold")
ax.set_xlabel("Customer Category")
ax.set_ylabel("Transaction Cost ($)")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.0f}"))
# Annotate median dollar value above each box for quick comparison
for i, cat in enumerate(order_cat):
    med = df.loc[df["Customer_Category"] == cat, "Total_Cost"].median()
    ax.text(i, med + 1.5, f"${med:.0f}", ha="center", fontsize=8)
sns.despine(ax=ax)
plt.tight_layout()
bp1 = BEHAVIOUR_DIR / "p1_spend_distribution_by_category.png"
fig.savefig(bp1, dpi=FIG_DPI, bbox_inches="tight"); plt.close()
print(f"  ✔ Saved: {bp1.name}")

# ── BP2: Average Spend by Day of Week (bar) ───────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 5))
dow_values = [dow_spend.get(d, 0) for d in DOW_ORDER]
bars = ax.bar(DOW_ORDER, dow_values, color=COLORS[:7], edgecolor="white")
ax.set_title("Average Transaction Spend by Day of Week", fontweight="bold")
ax.set_xlabel("Day of Week")
ax.set_ylabel("Avg Spend ($)")
for bar in bars:
    ax.text(bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.3,
            f"${bar.get_height():.2f}", ha="center", va="bottom", fontsize=9)
sns.despine(ax=ax)
plt.tight_layout()
bp2 = BEHAVIOUR_DIR / "p2_avg_spend_by_day_of_week.png"
fig.savefig(bp2, dpi=FIG_DPI, bbox_inches="tight"); plt.close()
print(f"  ✔ Saved: {bp2.name}")

# ── BP3: Average Spend by Payment Method (horizontal bar) ────────────────────
fig, ax = plt.subplots(figsize=(9, 5))
pay_sorted = pay_spend["Avg_Spend"].sort_values()   # ascending for horizontal bar
bars = ax.barh(pay_sorted.index, pay_sorted.values,
               color=COLORS[:len(pay_sorted)], edgecolor="white")
ax.set_title("Average Spend by Payment Method", fontweight="bold")
ax.set_xlabel("Avg Spend ($)")
for bar in bars:
    ax.text(bar.get_width() + 0.3,
            bar.get_y() + bar.get_height() / 2,
            f"${bar.get_width():.2f}", va="center", fontsize=9)
ax.set_xlim(0, pay_sorted.max() * 1.15)
sns.despine(ax=ax)
plt.tight_layout()
bp3 = BEHAVIOUR_DIR / "p3_avg_spend_by_payment_method.png"
fig.savefig(bp3, dpi=FIG_DPI, bbox_inches="tight"); plt.close()
print(f"  ✔ Saved: {bp3.name}")

# ── BP4: Customer Category × Store Type heatmap — count ──────────────────────
# Darker cells = more visits; reveals store preference per segment.
fig, ax = plt.subplots(figsize=(13, 5))
sns.heatmap(cat_store_count, annot=True, fmt="d", cmap="YlOrRd",
            linewidths=0.4, ax=ax, cbar_kws={"label": "Transaction Count"})
ax.set_title("Customer Category × Store Type  —  Transaction Count",
             fontweight="bold")
ax.set_xlabel("Store Type"); ax.set_ylabel("Customer Category")
plt.tight_layout()
bp4 = BEHAVIOUR_DIR / "p4_category_storetype_heatmap_count.png"
fig.savefig(bp4, dpi=FIG_DPI, bbox_inches="tight"); plt.close()
print(f"  ✔ Saved: {bp4.name}")

# ── BP5: Customer Category × Store Type heatmap — avg spend ──────────────────
# Identifies which category spends most in which store type.
fig, ax = plt.subplots(figsize=(13, 5))
sns.heatmap(cat_store_spend, annot=True, fmt=".0f", cmap="Blues",
            linewidths=0.4, ax=ax, cbar_kws={"label": "Avg Spend ($)"})
ax.set_title("Customer Category × Store Type  —  Average Spend ($)",
             fontweight="bold")
ax.set_xlabel("Store Type"); ax.set_ylabel("Customer Category")
plt.tight_layout()
bp5 = BEHAVIOUR_DIR / "p5_category_storetype_heatmap_avgspend.png"
fig.savefig(bp5, dpi=FIG_DPI, bbox_inches="tight"); plt.close()
print(f"  ✔ Saved: {bp5.name}")

# ── BP6: Store Type — Volume vs Avg Spend bubble chart ───────────────────────
# Bubble size ∝ total revenue; position encodes volume (x) and spend quality (y).
fig, ax = plt.subplots(figsize=(10, 6))
bubble_sizes = (store_vol["Total_Revenue"] / store_vol["Total_Revenue"].max() * 3000)
ax.scatter(store_vol["Transactions"], store_vol["Avg_Spend"],
           s=bubble_sizes, c=range(len(store_vol)),
           cmap="tab10", alpha=0.75, edgecolors="white", linewidth=1.5)
for idx, row in store_vol.iterrows():
    ax.annotate(idx, (row["Transactions"], row["Avg_Spend"]),
                textcoords="offset points", xytext=(7, 4), fontsize=9)
ax.set_title("Store Type: Volume vs Avg Spend\n(bubble size ∝ total revenue)",
             fontweight="bold")
ax.set_xlabel("Transaction Count"); ax.set_ylabel("Avg Spend ($)")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.0f}"))
sns.despine(ax=ax)
plt.tight_layout()
bp6 = BEHAVIOUR_DIR / "p6_storetype_volume_vs_avgspend_bubble.png"
fig.savefig(bp6, dpi=FIG_DPI, bbox_inches="tight"); plt.close()
print(f"  ✔ Saved: {bp6.name}")

# ── BP7: Discount Usage Rate by Store Type (bar) ─────────────────────────────
fig, ax = plt.subplots(figsize=(10, 5))
disc_sorted = store_discount.sort_values(ascending=False)
bars = ax.bar(disc_sorted.index, disc_sorted.values,
              color=COLORS[:len(disc_sorted)], edgecolor="white")
ax.set_title("Discount Usage Rate (%) by Store Type", fontweight="bold")
ax.set_xlabel("Store Type"); ax.set_ylabel("Discount Rate (%)")
ax.set_ylim(0, disc_sorted.max() * 1.18)
for bar in bars:
    ax.text(bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.3,
            f"{bar.get_height():.1f}%", ha="center", va="bottom", fontsize=9)
ax.tick_params(axis="x", rotation=20)
sns.despine(ax=ax)
plt.tight_layout()
bp7 = BEHAVIOUR_DIR / "p7_discount_rate_by_storetype.png"
fig.savefig(bp7, dpi=FIG_DPI, bbox_inches="tight"); plt.close()
print(f"  ✔ Saved: {bp7.name}")

# ── BP8: Store Type × Season transaction count heatmap ───────────────────────
# Reveals seasonal store traffic patterns — useful for staffing and promotions.
fig, ax = plt.subplots(figsize=(10, 6))
sns.heatmap(store_season, annot=True, fmt="d", cmap="Greens",
            linewidths=0.4, ax=ax, cbar_kws={"label": "Transaction Count"})
ax.set_title("Store Type × Season  —  Transaction Count", fontweight="bold")
ax.set_xlabel("Season"); ax.set_ylabel("Store Type")
plt.tight_layout()
bp8 = BEHAVIOUR_DIR / "p8_storetype_season_heatmap.png"
fig.savefig(bp8, dpi=FIG_DPI, bbox_inches="tight"); plt.close()
print(f"  ✔ Saved: {bp8.name}")


# =============================================================================
#  SECTION 8b — DISCOUNT / PROMOTION PLOTS  (saved to outputs/discount_plots/)
# =============================================================================
print("\n" + "=" * 60)
print("  SECTION 8b — DISCOUNT / PROMOTION PLOTS")
print("=" * 60)

# ── DP1: Discount vs No-Discount — Avg Spend & Revenue (side-by-side bar) ─────
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
labels   = ["No Discount", "Discount Applied"]
avg_vals = [compare.loc["No Discount",      "Avg_Spend"],
            compare.loc["Discount Applied", "Avg_Spend"]]

# Left sub-plot: avg spend
bars_a = axes[0].bar(labels, avg_vals, color=[COLORS[1], COLORS[0]],
                     edgecolor="white", width=0.5)
axes[0].set_title("Avg Spend: Discount vs No Discount", fontweight="bold")
axes[0].set_ylabel("Avg Transaction Spend ($)")
for bar in bars_a:
    axes[0].text(bar.get_x() + bar.get_width() / 2,
                 bar.get_height() + 0.3,
                 f"${bar.get_height():.2f}", ha="center", va="bottom",
                 fontsize=11, fontweight="bold")
axes[0].set_ylim(0, max(avg_vals) * 1.2)
sns.despine(ax=axes[0])

# Right sub-plot: total revenue
rev_vals = [compare.loc["No Discount",      "Total_Revenue"],
            compare.loc["Discount Applied", "Total_Revenue"]]
bars_b = axes[1].bar(labels, rev_vals, color=[COLORS[1], COLORS[0]],
                     edgecolor="white", width=0.5)
axes[1].set_title("Total Revenue: Discount vs No Discount", fontweight="bold")
axes[1].set_ylabel("Total Revenue ($)")
axes[1].yaxis.set_major_formatter(
    mticker.FuncFormatter(lambda x, _: f"${x/1000:.0f}k"))
for bar in bars_b:
    axes[1].text(bar.get_x() + bar.get_width() / 2,
                 bar.get_height() * 1.01,
                 f"${bar.get_height():,.0f}", ha="center", va="bottom",
                 fontsize=9, fontweight="bold")
sns.despine(ax=axes[1])
plt.suptitle("Discount Impact on Spend & Revenue", fontsize=14, fontweight="bold")
plt.tight_layout()
dp1 = DISCOUNT_DIR / "p1_discount_spend_revenue_comparison.png"
fig.savefig(dp1, dpi=FIG_DPI, bbox_inches="tight"); plt.close()
print(f"  ✔ Saved: {dp1.name}")

# ── DP2: Discount uptake rate by Customer Category (bar) ─────────────────────
fig, ax = plt.subplots(figsize=(11, 5))
cat_disc_sorted = cat_disc.sort_values(ascending=False)
bars = ax.bar(cat_disc_sorted.index, cat_disc_sorted.values,
              color=COLORS[:len(cat_disc_sorted)], edgecolor="white")
ax.set_title("Discount Uptake Rate (%) by Customer Category", fontweight="bold")
ax.set_xlabel("Customer Category"); ax.set_ylabel("Discount Rate (%)")
ax.set_ylim(0, cat_disc_sorted.max() * 1.18)
for bar in bars:
    ax.text(bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.3,
            f"{bar.get_height():.1f}%", ha="center", va="bottom", fontsize=9)
ax.tick_params(axis="x", rotation=20)
sns.despine(ax=ax)
plt.tight_layout()
dp2 = DISCOUNT_DIR / "p2_discount_uptake_by_category.png"
fig.savefig(dp2, dpi=FIG_DPI, bbox_inches="tight"); plt.close()
print(f"  ✔ Saved: {dp2.name}")

# ── DP3: Avg Spend by Promotion Type (bar) ────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 5))
promo_spend_sorted = promo_kpi["Avg_Spend"].sort_values(ascending=False)
bars = ax.bar(promo_spend_sorted.index, promo_spend_sorted.values,
              color=COLORS[:len(promo_spend_sorted)], edgecolor="white", width=0.5)
ax.set_title("Average Spend by Promotion Type", fontweight="bold")
ax.set_xlabel("Promotion Type"); ax.set_ylabel("Avg Spend ($)")
ax.set_ylim(0, promo_spend_sorted.max() * 1.2)
for bar in bars:
    ax.text(bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.3,
            f"${bar.get_height():.2f}", ha="center", va="bottom",
            fontsize=10, fontweight="bold")
sns.despine(ax=ax)
plt.tight_layout()
dp3 = DISCOUNT_DIR / "p3_avg_spend_by_promotion.png"
fig.savefig(dp3, dpi=FIG_DPI, bbox_inches="tight"); plt.close()
print(f"  ✔ Saved: {dp3.name}")

# ── DP4: Promotion Revenue Share (pie) ────────────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 6))
rev_by_promo = promo_overview["Total_Revenue"].sort_values(ascending=False)
wedges, texts, autotexts = ax.pie(
    rev_by_promo.values, labels=rev_by_promo.index, autopct="%1.1f%%",
    colors=COLORS[:len(rev_by_promo)], startangle=140, pctdistance=0.80,
    wedgeprops={"edgecolor": "white", "linewidth": 1.5},
)
for t in autotexts:
    t.set_fontsize(9)
ax.set_title("Revenue Share by Promotion Type", fontweight="bold")
plt.tight_layout()
dp4 = DISCOUNT_DIR / "p4_promotion_revenue_share_pie.png"
fig.savefig(dp4, dpi=FIG_DPI, bbox_inches="tight"); plt.close()
print(f"  ✔ Saved: {dp4.name}")

# ── DP5: Promotion × Customer Category heatmap (transaction count) ────────────
fig, ax = plt.subplots(figsize=(12, 6))
sns.heatmap(promo_cat, annot=True, fmt="d", cmap="YlOrRd",
            linewidths=0.4, ax=ax, cbar_kws={"label": "Transaction Count"})
ax.set_title("Promotion Type × Customer Category  —  Transaction Count",
             fontweight="bold")
ax.set_xlabel("Promotion Type"); ax.set_ylabel("Customer Category")
plt.tight_layout()
dp5 = DISCOUNT_DIR / "p5_promotion_category_heatmap.png"
fig.savefig(dp5, dpi=FIG_DPI, bbox_inches="tight"); plt.close()
print(f"  ✔ Saved: {dp5.name}")

# ── DP6: Seasonal Revenue & Avg Spend (dual-axis bar + line) ──────────────────
fig, ax1 = plt.subplots(figsize=(9, 5))
ax2     = ax1.twinx()
x_pos   = range(len(SEASON_ORDER))
rev_s   = season_kpi.loc[SEASON_ORDER, "Total_Revenue"]
avg_s   = season_kpi.loc[SEASON_ORDER, "Avg_Spend"]

bars_r = ax1.bar(x_pos, rev_s.values, color=COLORS[:4],
                 edgecolor="white", width=0.5, label="Total Revenue")
ax2.plot(x_pos, avg_s.values, color="tomato", marker="D",
         markersize=7, linewidth=2, label="Avg Spend", zorder=5)

ax1.set_xticks(x_pos); ax1.set_xticklabels(SEASON_ORDER)
ax1.set_title("Seasonal Revenue & Average Spend", fontweight="bold")
ax1.set_ylabel("Total Revenue ($)"); ax2.set_ylabel("Avg Spend ($)", color="tomato")
ax2.tick_params(axis="y", colors="tomato")
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1000:.0f}k"))
for bar in bars_r:
    ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() * 1.01,
             f"${bar.get_height():,.0f}", ha="center", va="bottom", fontsize=8)
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=9)
sns.despine(ax=ax1, right=False)
plt.tight_layout()
dp6 = DISCOUNT_DIR / "p6_seasonal_revenue_avgspend.png"
fig.savefig(dp6, dpi=FIG_DPI, bbox_inches="tight"); plt.close()
print(f"  ✔ Saved: {dp6.name}")

# ── DP7: Store Type preference per Season (heatmap) ───────────────────────────
fig, ax = plt.subplots(figsize=(13, 5))
sns.heatmap(season_store, annot=True, fmt="d", cmap="Blues",
            linewidths=0.4, ax=ax, cbar_kws={"label": "Transaction Count"})
ax.set_title("Season × Store Type  —  Transaction Count Heatmap", fontweight="bold")
ax.set_xlabel("Store Type"); ax.set_ylabel("Season")
plt.tight_layout()
dp7 = DISCOUNT_DIR / "p7_season_storetype_heatmap.png"
fig.savefig(dp7, dpi=FIG_DPI, bbox_inches="tight"); plt.close()
print(f"  ✔ Saved: {dp7.name}")

# ── DP8: Discount uptake rate by Season (bar) ─────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(SEASON_ORDER, [season_disc.get(s, 0) for s in SEASON_ORDER],
              color=COLORS[:4], edgecolor="white", width=0.5)
ax.set_title("Discount Uptake Rate (%) by Season", fontweight="bold")
ax.set_xlabel("Season"); ax.set_ylabel("Discount Rate (%)")
ax.set_ylim(0, season_disc.max() * 1.2)
for bar in bars:
    ax.text(bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.3,
            f"{bar.get_height():.1f}%", ha="center", va="bottom",
            fontsize=10, fontweight="bold")
sns.despine(ax=ax)
plt.tight_layout()
dp8 = DISCOUNT_DIR / "p8_discount_uptake_by_season.png"
fig.savefig(dp8, dpi=FIG_DPI, bbox_inches="tight"); plt.close()
print(f"  ✔ Saved: {dp8.name}")

# ── DP9: Promotion revenue contribution by Season (stacked bar) ───────────────
fig, ax = plt.subplots(figsize=(11, 5))
promo_season_rev.reindex(SEASON_ORDER).plot(
    kind="bar", stacked=True, ax=ax,
    color=COLORS[:len(promo_season_rev.columns)],
    edgecolor="white", linewidth=0.4, width=0.55,
)
ax.set_title("Promotion Revenue Contribution by Season (Stacked)", fontweight="bold")
ax.set_xlabel("Season"); ax.set_ylabel("Total Revenue ($)")
ax.set_xticklabels(SEASON_ORDER, rotation=0)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1000:.0f}k"))
ax.legend(title="Promotion Type", bbox_to_anchor=(1.01, 1),
          loc="upper left", fontsize=8, title_fontsize=8)
sns.despine(ax=ax)
plt.tight_layout()
dp9 = DISCOUNT_DIR / "p9_promotion_revenue_by_season_stacked.png"
fig.savefig(dp9, dpi=FIG_DPI, bbox_inches="tight"); plt.close()
print(f"  ✔ Saved: {dp9.name}")


# =============================================================================
#  SECTION 8c — SUMMARY DASHBOARD  (saved to outputs/plots/)
# =============================================================================
print("\n" + "=" * 60)
print("  SECTION 8c — SUMMARY DASHBOARD")
print("=" * 60)

fig = plt.figure(figsize=(22, 26))
fig.suptitle("Retail Transaction Analysis — Summary Dashboard",
             fontsize=20, fontweight="bold", y=0.995)
gs = GridSpec(4, 2, figure=fig, hspace=0.42, wspace=0.32)

# Panel 1 — Transactions per city (full-width bar at top)
ax1 = fig.add_subplot(gs[0, :])
city_counts = df["City"].value_counts().sort_values(ascending=False)
bars = ax1.bar(city_counts.index, city_counts.values,
               color=COLORS[:len(city_counts)], edgecolor="white", linewidth=0.6)
ax1.set_title("Number of Transactions per City", fontweight="bold")
ax1.set_xlabel("City"); ax1.set_ylabel("Transaction Count")
for bar in bars:
    ax1.text(bar.get_x() + bar.get_width() / 2,
             bar.get_height() + 3, str(int(bar.get_height())),
             ha="center", va="bottom", fontsize=9)
ax1.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
sns.despine(ax=ax1, left=False)

# Panel 2 — Payment method distribution (pie)
ax2 = fig.add_subplot(gs[1, 0])
pay_counts = df["Payment_Method"].value_counts()
_, _, autotexts = ax2.pie(
    pay_counts.values, labels=pay_counts.index, autopct="%1.1f%%",
    colors=COLORS[:len(pay_counts)], startangle=140, pctdistance=0.82,
    wedgeprops={"edgecolor": "white", "linewidth": 1.2},
)
for t in autotexts:
    t.set_fontsize(9)
ax2.set_title("Payment Method Distribution", fontweight="bold")

# Panel 3 — Monthly revenue trend (line, coloured by year)
ax3 = fig.add_subplot(gs[1, 1])
monthly_rev = (df.groupby(["Year", "Month"])["Total_Cost"]
               .sum().reset_index())
month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
for i, (yr, grp) in enumerate(monthly_rev.groupby("Year")):
    ax3.plot(grp["Month"], grp["Total_Cost"], marker="o", markersize=4,
             linewidth=1.8, label=str(yr), color=COLORS[i])
ax3.set_xticks(range(1, 13))
ax3.set_xticklabels(month_labels, fontsize=8)
ax3.set_title("Monthly Revenue Trend (by Year)", fontweight="bold")
ax3.set_xlabel("Month"); ax3.set_ylabel("Total Revenue ($)")
ax3.legend(title="Year", fontsize=8, title_fontsize=8)
ax3.yaxis.set_major_formatter(
    mticker.FuncFormatter(lambda x, _: f"${x/1000:.0f}k"))
sns.despine(ax=ax3, left=False)

# Panel 4 — Revenue by season & customer category (stacked bar, full-width)
ax4 = fig.add_subplot(gs[2, :])
rev_matrix.plot(kind="bar", stacked=True, ax=ax4,
                color=COLORS[:len(rev_matrix.columns)],
                edgecolor="white", linewidth=0.4, width=0.65)
ax4.set_title("Revenue by Season & Customer Category (Stacked Bar)",
              fontweight="bold")
ax4.set_xlabel("Season"); ax4.set_ylabel("Total Revenue ($)")
ax4.set_xticklabels(SEASON_ORDER, rotation=0)
ax4.yaxis.set_major_formatter(
    mticker.FuncFormatter(lambda x, _: f"${x/1000:.0f}k"))
ax4.legend(title="Customer Category", bbox_to_anchor=(1.01, 1),
           loc="upper left", fontsize=8, title_fontsize=8)
sns.despine(ax=ax4, left=False)

# Panel 5 — Avg spending per season (bar)
ax5 = fig.add_subplot(gs[3, 0])
bars5 = ax5.bar(avg_season_spend.index, avg_season_spend.values,
                color=COLORS[:4], edgecolor="white")
ax5.set_title("Average Spending per Season", fontweight="bold")
ax5.set_xlabel("Season"); ax5.set_ylabel("Avg Spend ($)")
for bar in bars5:
    ax5.text(bar.get_x() + bar.get_width() / 2,
             bar.get_height() + 0.3,
             f"${bar.get_height():.2f}", ha="center", va="bottom", fontsize=9)
sns.despine(ax=ax5, left=False)

# Panel 6 — Avg cost: Discount vs No Discount (horizontal bar)
ax6 = fig.add_subplot(gs[3, 1])
disc_vals = disc_avg["Avg_Cost"]
bars6 = ax6.barh(disc_vals.index, disc_vals.values,
                 color=[COLORS[2], COLORS[3]], edgecolor="white")
ax6.set_title("Avg Transaction Cost:\nDiscount vs No Discount", fontweight="bold")
ax6.set_xlabel("Avg Cost ($)")
for bar in bars6:
    ax6.text(bar.get_width() + 0.3,
             bar.get_y() + bar.get_height() / 2,
             f"${bar.get_width():.2f}", va="center", fontsize=10)
ax6.set_xlim(0, disc_vals.max() * 1.18)
sns.despine(ax=ax6, left=False)

# Save the dashboard
dash_path = DASHBOARD_DIR / "transaction_dashboard.png"
fig.savefig(dash_path, dpi=FIG_DPI, bbox_inches="tight")
plt.close()
print(f"\n  ✔ Dashboard saved → {dash_path}")


# =============================================================================
#  SECTION 9 — COMPREHENSIVE KEY INSIGHTS SUMMARY
# =============================================================================
print("\n" + "=" * 60)
print("  SECTION 9 — COMPREHENSIVE KEY INSIGHTS SUMMARY")
print("=" * 60)

print(f"""
╔══════════════════════════════════════════════════════════════╗
║           RETAIL ANALYSIS — FULL INSIGHTS REPORT            ║
╚══════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. DATASET OVERVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • {total_txn:,} total transactions | {df['Date'].min().year}–{df['Date'].max().year}
  • {unique_customers:,} unique customers across {df['City'].nunique()} cities
  • Best-selling product  : {top5_products.index[0]} ({top5_products.iloc[0]:,} appearances)
  • Most active city      : {top_cities.index[0]} ({top_cities.iloc[0]:,} transactions)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  2. CUSTOMER BEHAVIOUR — SPENDING PATTERNS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • Highest-spending category  : {spend_stats['Mean'].idxmax()}
      Avg ${spend_stats['Mean'].max():.2f}  |  Median ${spend_stats.loc[spend_stats['Mean'].idxmax(), 'Median']:.2f}
  • Lowest-spending category   : {spend_stats['Mean'].idxmin()}
      Avg ${spend_stats['Mean'].min():.2f}  |  Median ${spend_stats.loc[spend_stats['Mean'].idxmin(), 'Median']:.2f}
  • Largest average basket      : {basket.idxmax()} ({basket.max():.2f} items/txn)
  • Smallest average basket     : {basket.idxmin()} ({basket.min():.2f} items/txn)
  • Store type most items/txn   : {avg_items_store.index[0]} ({avg_items_store.iloc[0]} items)
  • Peak spending day           : {dow_spend.idxmax()} (${dow_spend.max():.2f} avg)
  • Lowest spending day         : {dow_spend.idxmin()} (${dow_spend.min():.2f} avg)
  • Highest-spend payment method: {pay_spend['Avg_Spend'].idxmax()} (${pay_spend['Avg_Spend'].max():.2f} avg)
  • Most-used payment method    : {pay_spend['Transactions'].idxmax()} ({pay_spend['Transactions'].max():,} txns)
  • Items ↔ Cost correlation    : {corr_val:.4f}
      {'(Strong — item count predicts spend well)' if abs(corr_val) > 0.5 else '(Moderate)' if abs(corr_val) > 0.2 else '(Weak — spend is independent of item count)'}
  • Most loyal category         : {freq_by_cat['Avg_Visits'].idxmax()} ({freq_by_cat['Avg_Visits'].max():.2f} avg visits)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  3. STORE-TYPE PREFERENCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • Most visited store type     : {store_vol['Transactions'].idxmax()} ({store_vol['Transactions'].max():,} visits)
  • Highest total revenue store : {store_vol['Total_Revenue'].idxmax()} (${store_vol['Total_Revenue'].max():,.2f})
  • Highest avg spend store     : {store_vol['Avg_Spend'].idxmax()} (${store_vol['Avg_Spend'].max():.2f} avg)
  • Highest discount-rate store : {store_discount.idxmax()} ({store_discount.max():.1f}% of transactions)
  • Lowest  discount-rate store : {store_discount.idxmin()} ({store_discount.min():.1f}% of transactions)

  Customer Category → Preferred Store Type:""")

for cat, store in pref_store.items():
    count = cat_store_count.loc[cat, store]
    print(f"    {cat:15s}  →  {store}  ({count:,} visits)")

print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  4. DISCOUNT vs NON-DISCOUNT TRANSACTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • {disc_count:,} transactions had a discount ({disc_count/total*100:.1f}% of all)
  • {no_disc_count:,} transactions had no discount ({no_disc_count/total*100:.1f}% of all)

  • Avg spend WITH discount        : ${compare.loc['Discount Applied','Avg_Spend']:.2f}
  • Avg spend WITHOUT discount     : ${compare.loc['No Discount','Avg_Spend']:.2f}
  • Spend difference per txn       : ${spend_diff:+.2f}

  • Total revenue WITH discount    : ${compare.loc['Discount Applied','Total_Revenue']:,.2f}
  • Total revenue WITHOUT discount : ${compare.loc['No Discount','Total_Revenue']:,.2f}
  • Revenue lift from discounts    : ${rev_lift:+,.2f}

  • Statistical significance (Welch t-test):
      t = {t_stat:.4f}  |  p = {p_value:.6f}
      → {'SIGNIFICANT — spend difference is statistically real (p < 0.05)' if p_value < 0.05 else 'NOT significant — difference may be random chance (p >= 0.05)'}

  • Highest discount users (category)  : {cat_disc.idxmax()} ({cat_disc.max():.1f}%)
  • Lowest  discount users (category)  : {cat_disc.idxmin()} ({cat_disc.min():.1f}%)
  • Store type with highest disc. rate : {store_disc.idxmax()} ({store_disc.max():.1f}%)
  • Store type with lowest  disc. rate : {store_disc.idxmin()} ({store_disc.min():.1f}%)
  • Peak discount season               : {season_disc.idxmax()} ({season_disc.max():.1f}%)
  • Lowest discount season             : {season_disc.idxmin()} ({season_disc.min():.1f}%)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  5. PROMOTION EFFECTIVENESS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • Most-used promotion overall       : {promo_overview['Transactions'].idxmax()}
      ({promo_overview['Transactions'].max():,} transactions, {promo_overview['Txn_Share_%'].max():.1f}% share)

  • Highest revenue promotion         : {promo_overview['Total_Revenue'].idxmax()}
      Revenue ${promo_overview['Total_Revenue'].max():,.2f}  ({promo_overview['Revenue_Share_%'].max():.1f}% of all revenue)

  • Highest avg-spend promotion       : {promo_kpi['Avg_Spend'].idxmax()}
      Avg spend ${promo_kpi['Avg_Spend'].max():.2f} per transaction

  • Largest basket promotion          : {promo_kpi['Avg_Items'].idxmax()}
      Avg {promo_kpi['Avg_Items'].max():.2f} items per transaction

  Best promotion per Customer Category (by avg spend):""")

for cat in best_promo_spend.index:
    best = best_promo_spend.loc[cat].idxmax()
    val  = best_promo_spend.loc[cat].max()
    print(f"    {cat:15s}  →  {best}  (${val:.2f} avg)")

print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  6. SEASONAL TRENDS & PREFERENCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • Highest revenue season  : {season_kpi['Total_Revenue'].idxmax()}
      ${season_kpi['Total_Revenue'].max():,.2f}  ({season_kpi.loc[season_kpi['Total_Revenue'].idxmax(),'Transactions']:,} transactions)
  • Lowest  revenue season  : {season_kpi['Total_Revenue'].idxmin()}
      ${season_kpi['Total_Revenue'].min():,.2f}  ({season_kpi.loc[season_kpi['Total_Revenue'].idxmin(),'Transactions']:,} transactions)
  • Highest avg spend season: {season_kpi['Avg_Spend'].idxmax()} (${season_kpi['Avg_Spend'].max():.2f})
  • Lowest  avg spend season: {season_kpi['Avg_Spend'].idxmin()} (${season_kpi['Avg_Spend'].min():.2f})

  Seasonal Preferences at a Glance:
  {'Season':<10} {'Best Store Type':<24} {'Top Payment':<22} {'Dominant Promo'}
  {'-'*82}""")

for s in SEASON_ORDER:
    store = pref_store_season.get(s, "N/A")
    pay   = pref_pay_season.get(s, "N/A")
    promo = dominant_promo_season.get(s, "N/A")
    print(f"  {s:<10} {store:<24} {pay:<22} {promo}")

print(f"""
  Top product per season:""")
for s in SEASON_ORDER:
    top_p = season_top_products[s]
    print(f"    {s:<8} → {top_p.index[0]} ({top_p.iloc[0]:,} times)")

print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  OUTPUT FILES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Behaviour plots  (8)  → {BEHAVIOUR_DIR}
  Discount  plots  (9)  → {DISCOUNT_DIR}
  Dashboard        (1)  → {DASHBOARD_DIR}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")

