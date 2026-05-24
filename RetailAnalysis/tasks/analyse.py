"""
=============================================================
  Customer Behaviour Insights
  ──────────────────────────
  Section A — Spending Patterns
      A1. Descriptive spend stats per customer category
      A2. Customer spend segmentation (Low / Mid / High)
      A3. Average spend by day of week
      A4. Average spend by payment method
      A5. Average basket size (items) by customer category
      A6. Correlation: Total_Items vs Total_Cost
      A7. Repeat-visit frequency per customer

  Section B — Store-Type Preferences
      B1. Overall volume, avg spend & revenue per store type
      B2. Customer category × store type (transaction count)
      B3. Customer category × store type (avg spend)
      B4. Most preferred store type per city
      B5. Discount usage rate per store type
      B6. Store type × season transaction count
      B7. Preferred payment method per store type

  Section C — Visualisations  (8 plots saved to outputs/behaviour_plots/)
=============================================================
"""

from pathlib import Path
import ast
import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")           # non-interactive backend — no display required
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).resolve().parent   # tasks/
PROJECT_ROOT = BASE_DIR.parent                   # RetailAnalysis/
DATA_FILE    = PROJECT_ROOT / "data" / "sample transaction.csv"
PLOTS_DIR    = PROJECT_ROOT / "outputs" / "behaviour_plots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)     # create folder if it doesn't exist

# ── Shared visual style ────────────────────────────────────────────────────────
PALETTE = "Set2"
FIG_DPI = 150
sns.set_theme(style="whitegrid", palette=PALETTE)
plt.rcParams.update({"axes.titlesize": 13, "axes.labelsize": 11,
                     "figure.dpi": FIG_DPI})
COLORS = sns.color_palette(PALETTE, 12)


# =============================================================================
#  LOAD & CLEAN DATA
# =============================================================================
# Read raw CSV (utf-8-sig handles optional BOM character)
df = pd.read_csv(DATA_FILE, encoding="utf-8-sig")

# Parse dates — format="mixed" handles both DD-MM-YYYY and YYYY-MM-DD variants
df["Date"] = pd.to_datetime(
    df["Date"], format="mixed", dayfirst=True, errors="coerce"
)
bad = df["Date"].isna().sum()
if bad:
    print(f"⚠  Warning: {bad} rows with unparseable dates set to NaT.")

# Extract temporal features used in spending-pattern analysis
df["Year"]      = df["Date"].dt.year
df["Month"]     = df["Date"].dt.month
df["MonthName"] = df["Date"].dt.strftime("%b")
df["DayOfWeek"] = df["Date"].dt.day_name()

# Normalise Discount_Applied string → Python bool
df["Discount_Applied"] = (
    df["Discount_Applied"]
    .astype(str).str.strip().str.upper()
    .map({"TRUE": True, "FALSE": False})
)

# Parse the product column — stored as a stringified Python list
def parse_products(raw):
    """Convert string representation of a list to an actual Python list."""
    try:
        return ast.literal_eval(str(raw))
    except Exception:
        return []

df["Product_List"] = df["Product"].apply(parse_products)

print(f"\nData loaded : {df.shape[0]:,} rows × {df.shape[1]} columns")
print(f"Date range  : {df['Date'].min().date()} → {df['Date'].max().date()}")


# =============================================================================
#  SECTION A — SPENDING PATTERNS
# =============================================================================
print("\n" + "="*60)
print("  SECTION A — SPENDING PATTERNS")
print("="*60)

# ── A1. Descriptive spend statistics per Customer Category ────────────────────
# Shows mean, median, spread, and extremes so we can compare categories fairly.
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
print("\nA1. Spend statistics by Customer Category:")
print(spend_stats.to_string())

# ── A2. Customer spend segmentation (Low / Mid / High) ───────────────────────
# Calculate each customer's TOTAL lifetime spend across all transactions,
# then bin into three equal-width segments for easy comparison.
cust_total = df.groupby("Customer_Name")["Total_Cost"].sum()
seg_labels = ["Low Spender", "Mid Spender", "High Spender"]
cust_segment = pd.cut(cust_total, bins=3, labels=seg_labels)

segment_counts = cust_segment.value_counts().reindex(seg_labels)
print("\nA2. Customer spend segments (by total lifetime spend):")
print(segment_counts.to_string())

# Attach segment label back to every transaction row for downstream use
df = df.merge(
    cust_segment.rename("Spend_Segment").reset_index(),
    on="Customer_Name", how="left"
)

# ── A3. Average spend by Day of Week ─────────────────────────────────────────
# Reveals whether weekends or specific weekdays drive higher basket values.
DOW_ORDER = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
dow_spend = (
    df.groupby("DayOfWeek")["Total_Cost"]
    .mean()
    .reindex(DOW_ORDER)
    .round(2)
)
print("\nA3. Average spend by Day of Week:")
print(dow_spend.to_string())
print(f"  ➜ Peak day    : {dow_spend.idxmax()}  (${dow_spend.max():.2f} avg)")
print(f"  ➜ Quietest day: {dow_spend.idxmin()} (${dow_spend.min():.2f} avg)")

# ── A4. Average spend & volume by Payment Method ─────────────────────────────
# Identifies whether digital payment users spend differently from cash users.
pay_spend = (
    df.groupby("Payment_Method")["Total_Cost"]
    .agg(Avg_Spend="mean", Transactions="count")
    .round(2)
    .sort_values("Avg_Spend", ascending=False)
)
print("\nA4. Avg spend & volume by Payment Method:")
print(pay_spend.to_string())
print(f"  ➜ Highest avg-spend method : {pay_spend['Avg_Spend'].idxmax()} "
      f"(${pay_spend['Avg_Spend'].max():.2f})")
print(f"  ➜ Most-used payment method : {pay_spend['Transactions'].idxmax()} "
      f"({pay_spend['Transactions'].max():,} txns)")

# ── A5. Average basket size (items) per Customer Category ────────────────────
# Larger baskets don't always mean higher spend — this cross-checks A1.
basket = (
    df.groupby("Customer_Category")["Total_Items"]
    .mean()
    .round(2)
    .sort_values(ascending=False)
)
print("\nA5. Average basket size (items) by Customer Category:")
print(basket.to_string())
print(f"  ➜ Largest average basket  : {basket.idxmax()} ({basket.max():.2f} items/txn)")
print(f"  ➜ Smallest average basket : {basket.idxmin()} ({basket.min():.2f} items/txn)")

# ── A6. Correlation — Total_Items vs Total_Cost ───────────────────────────────
# Pearson r tells us whether buying more items always means spending more.
corr_val = df[["Total_Items", "Total_Cost"]].corr().loc["Total_Items", "Total_Cost"]
print(f"\nA6. Pearson correlation — Total_Items vs Total_Cost : {corr_val:.4f}")
if abs(corr_val) > 0.5:
    print("  ➜ Strong relationship: more items strongly predict higher spend.")
elif abs(corr_val) > 0.2:
    print("  ➜ Moderate relationship between items purchased and spend.")
else:
    print("  ➜ Weak relationship — spend is largely independent of item count.")

# ── A7. Repeat-visit frequency per customer ───────────────────────────────────
# Counts how many transactions each customer made; then summarises by category.
visit_freq = df.groupby("Customer_Name")["Transaction_ID"].count().rename("Visit_Count")
df = df.merge(visit_freq.reset_index(), on="Customer_Name", how="left")

freq_by_cat = (
    df.drop_duplicates("Customer_Name")        # one row per customer
    .groupby("Customer_Category")["Visit_Count"]
    .agg(Avg_Visits="mean", Max_Visits="max")
    .round(2)
    .sort_values("Avg_Visits", ascending=False)
)
print("\nA7. Repeat-visit frequency per Customer Category:")
print(freq_by_cat.to_string())
print(f"  ➜ Most loyal category (avg visits): {freq_by_cat['Avg_Visits'].idxmax()} "
      f"({freq_by_cat['Avg_Visits'].max():.2f} visits)")


# =============================================================================
#  SECTION B — STORE-TYPE PREFERENCES
# =============================================================================
print("\n" + "="*60)
print("  SECTION B — STORE-TYPE PREFERENCES")
print("="*60)

# ── B1. Overall volume, avg spend & revenue per store type ────────────────────
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
print("\nB1. Store Type — Volume, Avg Spend, Total Revenue:")
print(store_vol.to_string())
print(f"  ➜ Most visited store       : {store_vol['Transactions'].idxmax()} "
      f"({store_vol['Transactions'].max():,} visits)")
print(f"  ➜ Highest avg spend        : {store_vol['Avg_Spend'].idxmax()} "
      f"(${store_vol['Avg_Spend'].max():.2f})")
print(f"  ➜ Highest total revenue    : {store_vol['Total_Revenue'].idxmax()} "
      f"(${store_vol['Total_Revenue'].max():,.2f})")

# ── B2. Customer Category × Store Type — transaction count ────────────────────
# Cross-tabulation reveals which customer segments shop where most frequently.
cat_store_count = pd.crosstab(df["Customer_Category"], df["Store_Type"])
print("\nB2. Customer Category × Store Type (transaction count):")
print(cat_store_count.to_string())

# Preferred store per category = column with the highest count
pref_store = cat_store_count.idxmax(axis=1)
print("\n  ➜ Most preferred store per Customer Category:")
for cat, store in pref_store.items():
    count = cat_store_count.loc[cat, store]
    print(f"     {cat:15s} → {store}  ({count:,} visits)")

# ── B3. Customer Category × Store Type — average spend ───────────────────────
# Highlights premium vs budget shopping behaviour per segment per store type.
cat_store_spend = (
    df.groupby(["Customer_Category", "Store_Type"])["Total_Cost"]
    .mean()
    .unstack()
    .round(2)
)
print("\nB3. Avg spend — Customer Category × Store Type:")
print(cat_store_spend.to_string())

# ── B4. Most preferred store type per city ────────────────────────────────────
# Useful for city-level stock allocation and store placement decisions.
city_store    = pd.crosstab(df["City"], df["Store_Type"])
pref_store_city = city_store.idxmax(axis=1)
print("\nB4. Most preferred store type by City:")
for city, store in pref_store_city.items():
    print(f"     {city:15s} → {store}")

# ── B5. Discount usage rate per store type ────────────────────────────────────
# Fraction of transactions with Discount_Applied == True, expressed as %.
store_discount = (
    df.groupby("Store_Type")["Discount_Applied"]
    .mean()          # True=1, False=0 → mean = fraction discounted
    .mul(100)
    .round(1)
    .sort_values(ascending=False)
    .rename("Discount_Rate_%")
)
print("\nB5. Discount usage rate (%) by Store Type:")
print(store_discount.to_string())
print(f"  ➜ Highest discount rate: {store_discount.idxmax()} "
      f"({store_discount.max():.1f}% of transactions)")
print(f"  ➜ Lowest  discount rate: {store_discount.idxmin()} "
      f"({store_discount.min():.1f}% of transactions)")

# ── B6. Store Type × Season transaction count ─────────────────────────────────
# Shows whether certain stores are seasonally busier than others.
SEASON_ORDER = ["Spring", "Summer", "Fall", "Winter"]
store_season = (
    df.groupby(["Store_Type", "Season"])
    .size()
    .unstack(fill_value=0)
    .reindex(columns=SEASON_ORDER)
)
print("\nB6. Transaction count — Store Type × Season:")
print(store_season.to_string())

# ── B7. Preferred payment method per store type ───────────────────────────────
# Tells us whether contactless/digital payment adoption varies by store format.
store_pay      = pd.crosstab(df["Store_Type"], df["Payment_Method"])
pref_pay_store = store_pay.idxmax(axis=1)
print("\nB7. Most-used payment method by Store Type:")
for store, pay in pref_pay_store.items():
    count = store_pay.loc[store, pay]
    print(f"     {store:20s} → {pay}  ({count:,} transactions)")


# =============================================================================
#  SECTION C — VISUALISATIONS
# =============================================================================
print("\n" + "="*60)
print("  SECTION C — GENERATING PLOTS")
print("="*60)

# ── Plot 1: Spend Distribution by Customer Category (box plot) ────────────────
# Box plot shows median, IQR, and outliers — more informative than a bar chart.
fig, ax = plt.subplots(figsize=(12, 6))
order = spend_stats.index.tolist()    # categories ordered high→low by mean spend
sns.boxplot(
    data=df, x="Customer_Category", y="Total_Cost",
    order=order, palette=PALETTE,
    width=0.55, fliersize=3, ax=ax
)
ax.set_title("Spending Distribution by Customer Category", fontweight="bold")
ax.set_xlabel("Customer Category")
ax.set_ylabel("Transaction Cost ($)")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.0f}"))
# Annotate median dollar value above each box for quick comparison
for i, cat in enumerate(order):
    med = df.loc[df["Customer_Category"] == cat, "Total_Cost"].median()
    ax.text(i, med + 1.5, f"${med:.0f}", ha="center", fontsize=8)
sns.despine(ax=ax)
plt.tight_layout()
p1 = PLOTS_DIR / "p1_spend_distribution_by_category.png"
fig.savefig(p1, dpi=FIG_DPI, bbox_inches="tight")
plt.close()
print(f"  ✔ Saved: {p1.name}")

# ── Plot 2: Average Spend by Day of Week (bar) ────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 5))
dow_values = [dow_spend.get(d, 0) for d in DOW_ORDER]
bars2 = ax.bar(DOW_ORDER, dow_values, color=COLORS[:7], edgecolor="white")
ax.set_title("Average Transaction Spend by Day of Week", fontweight="bold")
ax.set_xlabel("Day of Week")
ax.set_ylabel("Avg Spend ($)")
# Label bars with exact dollar amount
for bar in bars2:
    ax.text(bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.3,
            f"${bar.get_height():.2f}",
            ha="center", va="bottom", fontsize=9)
sns.despine(ax=ax)
plt.tight_layout()
p2 = PLOTS_DIR / "p2_avg_spend_by_day_of_week.png"
fig.savefig(p2, dpi=FIG_DPI, bbox_inches="tight")
plt.close()
print(f"  ✔ Saved: {p2.name}")

# ── Plot 3: Average Spend by Payment Method (horizontal bar) ─────────────────
fig, ax = plt.subplots(figsize=(9, 5))
pay_sorted = pay_spend["Avg_Spend"].sort_values()   # ascending for horizontal bar
bars3 = ax.barh(pay_sorted.index, pay_sorted.values,
                color=COLORS[:len(pay_sorted)], edgecolor="white")
ax.set_title("Average Spend by Payment Method", fontweight="bold")
ax.set_xlabel("Avg Spend ($)")
for bar in bars3:
    ax.text(bar.get_width() + 0.3,
            bar.get_y() + bar.get_height() / 2,
            f"${bar.get_width():.2f}", va="center", fontsize=9)
ax.set_xlim(0, pay_sorted.max() * 1.15)
sns.despine(ax=ax)
plt.tight_layout()
p3 = PLOTS_DIR / "p3_avg_spend_by_payment_method.png"
fig.savefig(p3, dpi=FIG_DPI, bbox_inches="tight")
plt.close()
print(f"  ✔ Saved: {p3.name}")

# ── Plot 4: Customer Category × Store Type heatmap — count ───────────────────
# Darker cells = more visits; reveals store preference per customer segment.
fig, ax = plt.subplots(figsize=(13, 5))
sns.heatmap(
    cat_store_count,
    annot=True, fmt="d", cmap="YlOrRd",
    linewidths=0.4, ax=ax,
    cbar_kws={"label": "Transaction Count"}
)
ax.set_title("Customer Category × Store Type  —  Transaction Count",
             fontweight="bold")
ax.set_xlabel("Store Type")
ax.set_ylabel("Customer Category")
plt.tight_layout()
p4 = PLOTS_DIR / "p4_category_storetype_heatmap_count.png"
fig.savefig(p4, dpi=FIG_DPI, bbox_inches="tight")
plt.close()
print(f"  ✔ Saved: {p4.name}")

# ── Plot 5: Customer Category × Store Type heatmap — avg spend ───────────────
# Identifies which category spends most in which store type.
fig, ax = plt.subplots(figsize=(13, 5))
sns.heatmap(
    cat_store_spend,
    annot=True, fmt=".0f", cmap="Blues",
    linewidths=0.4, ax=ax,
    cbar_kws={"label": "Avg Spend ($)"}
)
ax.set_title("Customer Category × Store Type  —  Average Spend ($)",
             fontweight="bold")
ax.set_xlabel("Store Type")
ax.set_ylabel("Customer Category")
plt.tight_layout()
p5 = PLOTS_DIR / "p5_category_storetype_heatmap_avgspend.png"
fig.savefig(p5, dpi=FIG_DPI, bbox_inches="tight")
plt.close()
print(f"  ✔ Saved: {p5.name}")

# ── Plot 6: Store Type — Volume vs Avg Spend bubble chart ────────────────────
# Bubble size = total revenue; position encodes volume (x) and spend quality (y).
fig, ax = plt.subplots(figsize=(10, 6))
bubble_sizes = (store_vol["Total_Revenue"] / store_vol["Total_Revenue"].max() * 3000)
ax.scatter(
    store_vol["Transactions"], store_vol["Avg_Spend"],
    s=bubble_sizes,
    c=range(len(store_vol)),
    cmap="tab10", alpha=0.75,
    edgecolors="white", linewidth=1.5
)
# Label each bubble with its store type name
for idx, row in store_vol.iterrows():
    ax.annotate(idx,
                (row["Transactions"], row["Avg_Spend"]),
                textcoords="offset points", xytext=(7, 4), fontsize=9)
ax.set_title("Store Type: Volume vs Avg Spend\n(bubble size ∝ total revenue)",
             fontweight="bold")
ax.set_xlabel("Transaction Count")
ax.set_ylabel("Avg Spend ($)")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.0f}"))
sns.despine(ax=ax)
plt.tight_layout()
p6 = PLOTS_DIR / "p6_storetype_volume_vs_avgspend_bubble.png"
fig.savefig(p6, dpi=FIG_DPI, bbox_inches="tight")
plt.close()
print(f"  ✔ Saved: {p6.name}")

# ── Plot 7: Discount Usage Rate by Store Type (bar) ──────────────────────────
fig, ax = plt.subplots(figsize=(10, 5))
disc_sorted = store_discount.sort_values(ascending=False)
bars7 = ax.bar(disc_sorted.index, disc_sorted.values,
               color=COLORS[:len(disc_sorted)], edgecolor="white")
ax.set_title("Discount Usage Rate (%) by Store Type", fontweight="bold")
ax.set_xlabel("Store Type")
ax.set_ylabel("Discount Rate (%)")
ax.set_ylim(0, disc_sorted.max() * 1.18)
for bar in bars7:
    ax.text(bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.3,
            f"{bar.get_height():.1f}%",
            ha="center", va="bottom", fontsize=9)
ax.tick_params(axis="x", rotation=20)
sns.despine(ax=ax)
plt.tight_layout()
p7 = PLOTS_DIR / "p7_discount_rate_by_storetype.png"
fig.savefig(p7, dpi=FIG_DPI, bbox_inches="tight")
plt.close()
print(f"  ✔ Saved: {p7.name}")

# ── Plot 8: Store Type × Season transaction count heatmap ────────────────────
# Reveals seasonal store traffic patterns — useful for staffing and promotions.
fig, ax = plt.subplots(figsize=(10, 6))
sns.heatmap(
    store_season,
    annot=True, fmt="d", cmap="Greens",
    linewidths=0.4, ax=ax,
    cbar_kws={"label": "Transaction Count"}
)
ax.set_title("Store Type × Season  —  Transaction Count", fontweight="bold")
ax.set_xlabel("Season")
ax.set_ylabel("Store Type")
plt.tight_layout()
p8 = PLOTS_DIR / "p8_storetype_season_heatmap.png"
fig.savefig(p8, dpi=FIG_DPI, bbox_inches="tight")
plt.close()
print(f"  ✔ Saved: {p8.name}")


# =============================================================================
#  KEY INSIGHTS SUMMARY
# =============================================================================
print("\n" + "="*60)
print("  CUSTOMER BEHAVIOUR — KEY INSIGHTS SUMMARY")
print("="*60)

print(f"""
SPENDING PATTERNS
─────────────────
• Highest-spending category  : {spend_stats['Mean'].idxmax()}
    Avg ${spend_stats['Mean'].max():.2f}  |  Median ${spend_stats.loc[spend_stats['Mean'].idxmax(), 'Median']:.2f}
• Lowest-spending category   : {spend_stats['Mean'].idxmin()}
    Avg ${spend_stats['Mean'].min():.2f}  |  Median ${spend_stats.loc[spend_stats['Mean'].idxmin(), 'Median']:.2f}
• Largest average basket      : {basket.idxmax()} ({basket.max():.2f} items/txn)
• Smallest average basket     : {basket.idxmin()} ({basket.min():.2f} items/txn)
• Peak spending day           : {dow_spend.idxmax()} (${dow_spend.max():.2f} avg)
• Lowest spending day         : {dow_spend.idxmin()} (${dow_spend.min():.2f} avg)
• Highest-spend payment method: {pay_spend['Avg_Spend'].idxmax()} (${pay_spend['Avg_Spend'].max():.2f} avg)
• Most-used payment method    : {pay_spend['Transactions'].idxmax()} ({pay_spend['Transactions'].max():,} txns)
• Items ↔ Cost correlation    : {corr_val:.4f}
• Most loyal category         : {freq_by_cat['Avg_Visits'].idxmax()} ({freq_by_cat['Avg_Visits'].max():.2f} avg visits)

STORE-TYPE PREFERENCES
──────────────────────
• Most visited store type     : {store_vol['Transactions'].idxmax()} ({store_vol['Transactions'].max():,} visits)
• Highest total revenue store : {store_vol['Total_Revenue'].idxmax()} (${store_vol['Total_Revenue'].max():,.2f})
• Highest avg spend store     : {store_vol['Avg_Spend'].idxmax()} (${store_vol['Avg_Spend'].max():.2f} avg)
• Highest discount-rate store : {store_discount.idxmax()} ({store_discount.max():.1f}% of transactions)
• Lowest  discount-rate store : {store_discount.idxmin()} ({store_discount.min():.1f}% of transactions)

Customer Category → Preferred Store Type:""")

for cat, store in pref_store.items():
    count = cat_store_count.loc[cat, store]
    print(f"  {cat:15s}  →  {store}  ({count:,} visits)")

print(f"\nAll plots saved to: {PLOTS_DIR}")
