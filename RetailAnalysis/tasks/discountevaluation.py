"""
=============================================================
  Discount & Promotion Evaluation + Seasonal Trends
  ──────────────────────────────────────────────────
  Section A — Discount vs Non-Discount Transactions
      A1. Volume & percentage split
      A2. Avg spend, items, and revenue comparison
      A3. Discount uptake by Customer Category
      A4. Discount uptake by Store Type
      A5. Discount uptake by Season
      A6. Discount uptake by Payment Method
      A7. Statistical significance test (t-test)

  Section B — Promotion Effectiveness
      B1. Transaction count & revenue per promotion type
      B2. Avg spend & items per promotion type
      B3. Promotion uptake by Customer Category (heatmap)
      B4. Promotion type usage by Store Type
      B5. Promotion revenue share per Season
      B6. Best-performing promotion per Customer Category

  Section C — Seasonal Trends & Preferences
      C1. Revenue, transaction count & avg spend per season
      C2. Season-over-season growth (YoY)
      C3. Top-5 products per season
      C4. Preferred store type per season
      C5. Preferred payment method per season
      C6. Customer category distribution per season
      C7. Promotion type dominance per season

  Section D — Visualisations  (9 plots → outputs/discount_plots/)
  Section E — Key Insights Summary (printed)
=============================================================
"""

from pathlib import Path
import ast
import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
from scipy import stats            # for two-sample t-test in A7
import matplotlib
matplotlib.use("Agg")              # non-interactive backend, no display needed
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).resolve().parent   # tasks/
PROJECT_ROOT = BASE_DIR.parent                   # RetailAnalysis/
DATA_FILE    = PROJECT_ROOT / "data" / "sample transaction.csv"
PLOTS_DIR    = PROJECT_ROOT / "outputs" / "discount_plots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)     # create folder if absent

# ── Shared visual style ────────────────────────────────────────────────────────
PALETTE  = "Set2"
FIG_DPI  = 150
sns.set_theme(style="whitegrid", palette=PALETTE)
plt.rcParams.update({"axes.titlesize": 13, "axes.labelsize": 11,
                     "figure.dpi": FIG_DPI})
COLORS = sns.color_palette(PALETTE, 12)

SEASON_ORDER = ["Spring", "Summer", "Fall", "Winter"]


# =============================================================================
#  LOAD & CLEAN DATA
# =============================================================================
df = pd.read_csv(DATA_FILE, encoding="utf-8-sig")

# Parse dates — handles mixed formats like DD-MM-YYYY HH:MM and YYYY-MM-DD
df["Date"] = pd.to_datetime(
    df["Date"], format="mixed", dayfirst=True, errors="coerce"
)
bad = df["Date"].isna().sum()
if bad:
    print(f"⚠  {bad} rows with unparseable dates set to NaT.")

# Extract temporal features
df["Year"]      = df["Date"].dt.year
df["Month"]     = df["Date"].dt.month
df["MonthName"] = df["Date"].dt.strftime("%b")
df["Quarter"]   = df["Date"].dt.quarter

# Normalise Discount_Applied string → Python bool
df["Discount_Applied"] = (
    df["Discount_Applied"]
    .astype(str).str.strip().str.upper()
    .map({"TRUE": True, "FALSE": False})
)
# Fill missing Promotion values with the string "None"
# (avoids str vs float comparison errors throughout the script)
df["Promotion"] = df["Promotion"].fillna("None").str.strip()

# Parse Product column (stored as a stringified Python list)
def parse_products(raw):
    """Convert string repr of list  e.g. "['Milk','Bread']"  →  ['Milk', 'Bread']."""
    try:
        return ast.literal_eval(str(raw))
    except Exception:
        return []

df["Product_List"] = df["Product"].apply(parse_products)

# Convenience boolean mask — used throughout
disc   = df["Discount_Applied"] == True
no_disc = df["Discount_Applied"] == False

print(f"\nData loaded : {df.shape[0]:,} rows  ×  {df.shape[1]} columns")
print(f"Date range  : {df['Date'].min().date()} → {df['Date'].max().date()}")
print(f"Promotions  : {sorted(df['Promotion'].dropna().unique())}")
print(f"Seasons     : {sorted(df['Season'].unique())}")


# =============================================================================
#  SECTION A — DISCOUNT vs NON-DISCOUNT TRANSACTIONS
# =============================================================================
print("\n" + "="*60)
print("  SECTION A — DISCOUNT vs NON-DISCOUNT ANALYSIS")
print("="*60)

# ── A1. Volume & percentage split ─────────────────────────────────────────────
disc_count    = disc.sum()
no_disc_count = no_disc.sum()
total         = len(df)

print(f"\nA1. Transaction Volume Split:")
print(f"  Discount Applied    : {disc_count:,}  ({disc_count/total*100:.1f}%)")
print(f"  No Discount         : {no_disc_count:,}  ({no_disc_count/total*100:.1f}%)")
print(f"  Total Transactions  : {total:,}")

# ── A2. Avg spend, avg items, and total revenue comparison ────────────────────
# Compare key KPIs side-by-side for discounted vs non-discounted transactions.
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
print("\nA2. KPI Comparison — Discounted vs Non-Discounted:")
print(compare.to_string())

rev_lift = (
    compare.loc["Discount Applied","Total_Revenue"]
    - compare.loc["No Discount","Total_Revenue"]
)
spend_diff = (
    compare.loc["Discount Applied","Avg_Spend"]
    - compare.loc["No Discount","Avg_Spend"]
)
print(f"\n  ➜ Revenue difference   : ${rev_lift:+,.2f}  "
      f"({'discounted earns more' if rev_lift > 0 else 'no-discount earns more'})")
print(f"  ➜ Avg spend difference : ${spend_diff:+.2f} per transaction")

# ── A3. Discount uptake rate by Customer Category ─────────────────────────────
# Shows which customer segments use discounts most often.
cat_disc = (
    df.groupby("Customer_Category")["Discount_Applied"]
    .mean()
    .mul(100).round(1)
    .sort_values(ascending=False)
    .rename("Discount_Rate_%")
)
print("\nA3. Discount uptake rate (%) by Customer Category:")
print(cat_disc.to_string())
print(f"  ➜ Highest discount users: {cat_disc.idxmax()} ({cat_disc.max():.1f}%)")
print(f"  ➜ Lowest  discount users: {cat_disc.idxmin()} ({cat_disc.min():.1f}%)")

# Avg spend WITH vs WITHOUT discount, per customer category
cat_disc_spend = (
    df.groupby(["Customer_Category", "Discount_Applied"])["Total_Cost"]
    .mean()
    .unstack()
    .round(2)
)
cat_disc_spend.columns = ["No Discount", "Discount Applied"]
print("\n  Avg spend with vs without discount per Customer Category:")
print(cat_disc_spend.to_string())

# ── A4. Discount uptake rate by Store Type ────────────────────────────────────
store_disc = (
    df.groupby("Store_Type")["Discount_Applied"]
    .mean()
    .mul(100).round(1)
    .sort_values(ascending=False)
    .rename("Discount_Rate_%")
)
print("\nA4. Discount uptake rate (%) by Store Type:")
print(store_disc.to_string())
print(f"  ➜ Highest: {store_disc.idxmax()} ({store_disc.max():.1f}%)  "
      f"| Lowest: {store_disc.idxmin()} ({store_disc.min():.1f}%)")

# ── A5. Discount uptake rate by Season ────────────────────────────────────────
season_disc = (
    df.groupby("Season")["Discount_Applied"]
    .mean()
    .mul(100).round(1)
    .reindex(SEASON_ORDER)
    .rename("Discount_Rate_%")
)
print("\nA5. Discount uptake rate (%) by Season:")
print(season_disc.to_string())
print(f"  ➜ Peak discount season: {season_disc.idxmax()} ({season_disc.max():.1f}%)")

# ── A6. Discount uptake rate by Payment Method ────────────────────────────────
pay_disc = (
    df.groupby("Payment_Method")["Discount_Applied"]
    .mean()
    .mul(100).round(1)
    .sort_values(ascending=False)
    .rename("Discount_Rate_%")
)
print("\nA6. Discount uptake rate (%) by Payment Method:")
print(pay_disc.to_string())

# ── A7. Statistical significance — t-test on spend ────────────────────────────
# Tests whether the avg spend difference between the two groups is statistically
# significant (p < 0.05 = significant, p ≥ 0.05 = could be random chance).
disc_spend_vals    = df.loc[disc,    "Total_Cost"].dropna()
no_disc_spend_vals = df.loc[no_disc, "Total_Cost"].dropna()

t_stat, p_value = stats.ttest_ind(disc_spend_vals, no_disc_spend_vals,
                                   equal_var=False)   # Welch's t-test
print(f"\nA7. Welch's t-test — Discounted vs Non-Discounted spend:")
print(f"  t-statistic : {t_stat:.4f}")
print(f"  p-value     : {p_value:.6f}")
if p_value < 0.05:
    print("  ➜ SIGNIFICANT — spend difference is statistically real (p < 0.05).")
else:
    print("  ➜ NOT significant — difference may be due to chance (p ≥ 0.05).")


# =============================================================================
#  SECTION B — PROMOTION EFFECTIVENESS
# =============================================================================
print("\n" + "="*60)
print("  SECTION B — PROMOTION EFFECTIVENESS")
print("="*60)

# ── B1. Transaction count and total revenue per promotion type ────────────────
promo_overview = (
    df.groupby("Promotion")
    .agg(
        Transactions  = ("Transaction_ID", "count"),
        Total_Revenue = ("Total_Cost",      "sum"),
        Revenue_Share = ("Total_Cost",      "sum"),    # recalculated below
    )
    .round(2)
    .sort_values("Total_Revenue", ascending=False)
)
# Convert revenue to % share of all revenue
total_rev = df["Total_Cost"].sum()
promo_overview["Revenue_Share_%"] = (
    promo_overview["Total_Revenue"] / total_rev * 100
).round(1)
promo_overview["Txn_Share_%"] = (
    promo_overview["Transactions"] / total * 100
).round(1)
promo_overview = promo_overview.drop(columns="Revenue_Share")
print("\nB1. Promotion type — transactions, revenue & share:")
print(promo_overview.to_string())

# ── B2. Avg spend and avg items per promotion type ────────────────────────────
# A higher avg spend under a promotion = promotion drives bigger baskets.
promo_kpi = (
    df.groupby("Promotion")
    .agg(
        Avg_Spend = ("Total_Cost",   "mean"),
        Med_Spend = ("Total_Cost",   "median"),
        Avg_Items = ("Total_Items",  "mean"),
    )
    .round(2)
    .sort_values("Avg_Spend", ascending=False)
)
print("\nB2. Avg spend, median spend & avg items by Promotion Type:")
print(promo_kpi.to_string())
print(f"\n  ➜ Highest avg-spend promotion : {promo_kpi['Avg_Spend'].idxmax()} "
      f"(${promo_kpi['Avg_Spend'].max():.2f})")
print(f"  ➜ Largest basket promotion    : {promo_kpi['Avg_Items'].idxmax()} "
      f"({promo_kpi['Avg_Items'].max():.2f} items avg)")

# ── B3. Promotion uptake by Customer Category ─────────────────────────────────
# Cross-tab of transaction counts — shows which promotions resonate with
# which customer segments.
promo_cat = pd.crosstab(df["Customer_Category"], df["Promotion"])
print("\nB3. Promotion type × Customer Category (transaction count):")
print(promo_cat.to_string())

# Best promotion per customer category (highest transaction count)
best_promo_per_cat = promo_cat.idxmax(axis=1)
print("\n  ➜ Most-used promotion per Customer Category:")
for cat, promo in best_promo_per_cat.items():
    print(f"     {cat:15s} → {promo}  ({promo_cat.loc[cat, promo]:,} txns)")

# ── B4. Promotion usage by Store Type ─────────────────────────────────────────
promo_store = pd.crosstab(df["Store_Type"], df["Promotion"])
print("\nB4. Promotion type × Store Type (transaction count):")
print(promo_store.to_string())

best_promo_per_store = promo_store.idxmax(axis=1)
print("\n  ➜ Most-used promotion per Store Type:")
for store, promo in best_promo_per_store.items():
    print(f"     {store:20s} → {promo}  ({promo_store.loc[store, promo]:,} txns)")

# ── B5. Promotion revenue share per Season ────────────────────────────────────
promo_season_rev = (
    df.groupby(["Season", "Promotion"])["Total_Cost"]
    .sum()
    .unstack(fill_value=0)
    .reindex(SEASON_ORDER)
    .round(2)
)
# Convert each row to % of seasonal total for fair comparison
promo_season_pct = promo_season_rev.div(promo_season_rev.sum(axis=1), axis=0).mul(100).round(1)
print("\nB5. Promotion revenue share (%) by Season:")
print(promo_season_pct.to_string())

# ── B6. Best-performing promotion per Customer Category (by avg spend) ─────────
best_promo_spend = (
    df.groupby(["Customer_Category", "Promotion"])["Total_Cost"]
    .mean()
    .unstack()
    .round(2)
)
print("\nB6. Avg spend per Customer Category × Promotion Type:")
print(best_promo_spend.to_string())
print("\n  ➜ Best promotion (highest avg spend) per Customer Category:")
for cat in best_promo_spend.index:
    best = best_promo_spend.loc[cat].idxmax()
    val  = best_promo_spend.loc[cat].max()
    print(f"     {cat:15s} → {best}  (${val:.2f} avg)")


# =============================================================================
#  SECTION C — SEASONAL TRENDS & PREFERENCES
# =============================================================================
print("\n" + "="*60)
print("  SECTION C — SEASONAL TRENDS & PREFERENCES")
print("="*60)

# ── C1. Revenue, transaction count and avg spend per season ───────────────────
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
print("\nC1. Core KPIs per Season:")
print(season_kpi.to_string())
print(f"\n  ➜ Highest revenue season : {season_kpi['Total_Revenue'].idxmax()} "
      f"(${season_kpi['Total_Revenue'].max():,.2f})")
print(f"  ➜ Lowest  revenue season : {season_kpi['Total_Revenue'].idxmin()} "
      f"(${season_kpi['Total_Revenue'].min():,.2f})")
print(f"  ➜ Highest avg spend      : {season_kpi['Avg_Spend'].idxmax()} "
      f"(${season_kpi['Avg_Spend'].max():.2f})")

# ── C2. Season-over-season growth — annual revenue per season ─────────────────
# Pivots Year × Season to show how each season's revenue changes year-on-year.
yoy = (
    df.groupby(["Year", "Season"])["Total_Cost"]
    .sum()
    .unstack()
    .reindex(columns=SEASON_ORDER)
    .round(2)
)
print("\nC2. Annual Revenue per Season (Year × Season):")
print(yoy.to_string())

# Calculate % growth for each season between first and last year in data
first_yr, last_yr = yoy.index.min(), yoy.index.max()
if first_yr != last_yr:
    growth = ((yoy.loc[last_yr] - yoy.loc[first_yr]) / yoy.loc[first_yr] * 100).round(1)
    print(f"\n  Revenue growth {first_yr} → {last_yr} per season:")
    for s, g in growth.items():
        print(f"     {s:8s}: {g:+.1f}%")

# ── C3. Top-5 products per season ─────────────────────────────────────────────
print("\nC3. Top-5 products per Season:")
season_top_products = {}
for season in SEASON_ORDER:
    # Flatten all product lists for this season into one list
    all_prods = [
        p for sublist in df.loc[df["Season"] == season, "Product_List"]
        for p in sublist
    ]
    top5 = pd.Series(all_prods).value_counts().head(5)
    season_top_products[season] = top5
    print(f"\n  {season}:")
    for prod, cnt in top5.items():
        print(f"     {prod:25s} {cnt:,} times")

# ── C4. Preferred store type per season ───────────────────────────────────────
season_store = (
    df.groupby(["Season", "Store_Type"])
    .size()
    .unstack(fill_value=0)
    .reindex(SEASON_ORDER)
)
print("\nC4. Transaction count — Season × Store Type:")
print(season_store.to_string())

pref_store_season = season_store.idxmax(axis=1)
print("\n  ➜ Most visited store type per Season:")
for s, st in pref_store_season.items():
    print(f"     {s:8s} → {st}  ({season_store.loc[s, st]:,} visits)")

# ── C5. Preferred payment method per season ───────────────────────────────────
season_pay = (
    df.groupby(["Season", "Payment_Method"])
    .size()
    .unstack(fill_value=0)
    .reindex(SEASON_ORDER)
)
pref_pay_season = season_pay.idxmax(axis=1)
print("\nC5. Most-used payment method per Season:")
for s, pay in pref_pay_season.items():
    count = season_pay.loc[s, pay]
    print(f"     {s:8s} → {pay}  ({count:,} transactions)")

# ── C6. Customer category distribution per season ─────────────────────────────
# Shows whether certain customer segments shop more in specific seasons.
season_cat = (
    df.groupby(["Season", "Customer_Category"])
    .size()
    .unstack(fill_value=0)
    .reindex(SEASON_ORDER)
)
print("\nC6. Customer Category distribution per Season:")
print(season_cat.to_string())

dominant_cat_season = season_cat.idxmax(axis=1)
print("\n  ➜ Dominant Customer Category per Season:")
for s, cat in dominant_cat_season.items():
    print(f"     {s:8s} → {cat}  ({season_cat.loc[s, cat]:,} transactions)")

# ── C7. Promotion type dominance per season ───────────────────────────────────
season_promo = (
    df.groupby(["Season", "Promotion"])
    .size()
    .unstack(fill_value=0)
    .reindex(SEASON_ORDER)
)
dominant_promo_season = season_promo.idxmax(axis=1)
print("\nC7. Dominant Promotion Type per Season:")
for s, promo in dominant_promo_season.items():
    cnt = season_promo.loc[s, promo]
    print(f"     {s:8s} → {promo}  ({cnt:,} transactions)")


# =============================================================================
#  SECTION D — VISUALISATIONS
# =============================================================================
print("\n" + "="*60)
print("  SECTION D — GENERATING PLOTS")
print("="*60)

# ── Plot 1: Discount vs No-Discount — Avg Spend & Revenue (side-by-side bar) ──
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

# Left: avg spend comparison
labels  = ["No Discount", "Discount Applied"]
avg_vals = [
    compare.loc["No Discount",       "Avg_Spend"],
    compare.loc["Discount Applied",  "Avg_Spend"],
]
bars = axes[0].bar(labels, avg_vals,
                   color=[COLORS[1], COLORS[0]], edgecolor="white", width=0.5)
axes[0].set_title("Avg Spend: Discount vs No Discount", fontweight="bold")
axes[0].set_ylabel("Avg Transaction Spend ($)")
for bar in bars:
    axes[0].text(bar.get_x() + bar.get_width() / 2,
                 bar.get_height() + 0.3,
                 f"${bar.get_height():.2f}",
                 ha="center", va="bottom", fontsize=11, fontweight="bold")
axes[0].set_ylim(0, max(avg_vals) * 1.2)
sns.despine(ax=axes[0])

# Right: total revenue comparison
rev_vals = [
    compare.loc["No Discount",       "Total_Revenue"],
    compare.loc["Discount Applied",  "Total_Revenue"],
]
bars2 = axes[1].bar(labels, rev_vals,
                    color=[COLORS[1], COLORS[0]], edgecolor="white", width=0.5)
axes[1].set_title("Total Revenue: Discount vs No Discount", fontweight="bold")
axes[1].set_ylabel("Total Revenue ($)")
axes[1].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1000:.0f}k"))
for bar in bars2:
    axes[1].text(bar.get_x() + bar.get_width() / 2,
                 bar.get_height() * 1.01,
                 f"${bar.get_height():,.0f}",
                 ha="center", va="bottom", fontsize=9, fontweight="bold")
sns.despine(ax=axes[1])

plt.suptitle("Discount Impact on Spend & Revenue", fontsize=14, fontweight="bold")
plt.tight_layout()
p1 = PLOTS_DIR / "p1_discount_spend_revenue_comparison.png"
fig.savefig(p1, dpi=FIG_DPI, bbox_inches="tight")
plt.close()
print(f"  ✔ Saved: {p1.name}")

# ── Plot 2: Discount uptake rate by Customer Category (bar) ───────────────────
fig, ax = plt.subplots(figsize=(11, 5))
cat_disc_sorted = cat_disc.sort_values(ascending=False)
bars3 = ax.bar(cat_disc_sorted.index, cat_disc_sorted.values,
               color=COLORS[:len(cat_disc_sorted)], edgecolor="white")
ax.set_title("Discount Uptake Rate (%) by Customer Category", fontweight="bold")
ax.set_xlabel("Customer Category")
ax.set_ylabel("Discount Rate (%)")
ax.set_ylim(0, cat_disc_sorted.max() * 1.18)
for bar in bars3:
    ax.text(bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.3,
            f"{bar.get_height():.1f}%",
            ha="center", va="bottom", fontsize=9)
ax.tick_params(axis="x", rotation=20)
sns.despine(ax=ax)
plt.tight_layout()
p2 = PLOTS_DIR / "p2_discount_uptake_by_category.png"
fig.savefig(p2, dpi=FIG_DPI, bbox_inches="tight")
plt.close()
print(f"  ✔ Saved: {p2.name}")

# ── Plot 3: Avg Spend by Promotion Type (bar) ─────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 5))
promo_spend_sorted = promo_kpi["Avg_Spend"].sort_values(ascending=False)
bars4 = ax.bar(promo_spend_sorted.index, promo_spend_sorted.values,
               color=COLORS[:len(promo_spend_sorted)], edgecolor="white", width=0.5)
ax.set_title("Average Spend by Promotion Type", fontweight="bold")
ax.set_xlabel("Promotion Type")
ax.set_ylabel("Avg Spend ($)")
ax.set_ylim(0, promo_spend_sorted.max() * 1.2)
for bar in bars4:
    ax.text(bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.3,
            f"${bar.get_height():.2f}",
            ha="center", va="bottom", fontsize=10, fontweight="bold")
sns.despine(ax=ax)
plt.tight_layout()
p3 = PLOTS_DIR / "p3_avg_spend_by_promotion.png"
fig.savefig(p3, dpi=FIG_DPI, bbox_inches="tight")
plt.close()
print(f"  ✔ Saved: {p3.name}")

# ── Plot 4: Promotion Revenue Share (pie) ─────────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 6))
rev_by_promo = promo_overview["Total_Revenue"].sort_values(ascending=False)
wedges, texts, autotexts = ax.pie(
    rev_by_promo.values,
    labels=rev_by_promo.index,
    autopct="%1.1f%%",
    colors=COLORS[:len(rev_by_promo)],
    startangle=140,
    pctdistance=0.80,
    wedgeprops={"edgecolor": "white", "linewidth": 1.5},
)
for t in autotexts:
    t.set_fontsize(9)
ax.set_title("Revenue Share by Promotion Type", fontweight="bold")
plt.tight_layout()
p4 = PLOTS_DIR / "p4_promotion_revenue_share_pie.png"
fig.savefig(p4, dpi=FIG_DPI, bbox_inches="tight")
plt.close()
print(f"  ✔ Saved: {p4.name}")

# ── Plot 5: Promotion × Customer Category heatmap (transaction count) ─────────
fig, ax = plt.subplots(figsize=(12, 6))
sns.heatmap(
    promo_cat,
    annot=True, fmt="d", cmap="YlOrRd",
    linewidths=0.4, ax=ax,
    cbar_kws={"label": "Transaction Count"},
)
ax.set_title("Promotion Type × Customer Category  —  Transaction Count",
             fontweight="bold")
ax.set_xlabel("Promotion Type")
ax.set_ylabel("Customer Category")
plt.tight_layout()
p5 = PLOTS_DIR / "p5_promotion_category_heatmap.png"
fig.savefig(p5, dpi=FIG_DPI, bbox_inches="tight")
plt.close()
print(f"  ✔ Saved: {p5.name}")

# ── Plot 6: Seasonal Revenue & Avg Spend (dual-axis bar+line) ─────────────────
fig, ax1 = plt.subplots(figsize=(9, 5))
ax2 = ax1.twinx()    # second y-axis shares the same x-axis

x_pos = range(len(SEASON_ORDER))
rev_vals_season = season_kpi.loc[SEASON_ORDER, "Total_Revenue"]
avg_vals_season = season_kpi.loc[SEASON_ORDER, "Avg_Spend"]

# Bar = total revenue (left axis)
bars_s = ax1.bar(x_pos, rev_vals_season.values,
                 color=COLORS[:4], edgecolor="white", width=0.5, label="Total Revenue")
# Line = avg spend (right axis)
ax2.plot(x_pos, avg_vals_season.values,
         color="tomato", marker="D", markersize=7,
         linewidth=2, label="Avg Spend", zorder=5)

ax1.set_xticks(x_pos)
ax1.set_xticklabels(SEASON_ORDER)
ax1.set_title("Seasonal Revenue & Average Spend", fontweight="bold")
ax1.set_ylabel("Total Revenue ($)")
ax2.set_ylabel("Avg Spend ($)", color="tomato")
ax2.tick_params(axis="y", colors="tomato")
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1000:.0f}k"))

# Annotate bars with revenue labels
for bar in bars_s:
    ax1.text(bar.get_x() + bar.get_width() / 2,
             bar.get_height() * 1.01,
             f"${bar.get_height():,.0f}",
             ha="center", va="bottom", fontsize=8)

# Combined legend
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=9)
sns.despine(ax=ax1, right=False)
plt.tight_layout()
p6 = PLOTS_DIR / "p6_seasonal_revenue_avgspend.png"
fig.savefig(p6, dpi=FIG_DPI, bbox_inches="tight")
plt.close()
print(f"  ✔ Saved: {p6.name}")

# ── Plot 7: Store Type preference per Season (heatmap) ────────────────────────
fig, ax = plt.subplots(figsize=(13, 5))
sns.heatmap(
    season_store,
    annot=True, fmt="d", cmap="Blues",
    linewidths=0.4, ax=ax,
    cbar_kws={"label": "Transaction Count"},
)
ax.set_title("Season × Store Type  —  Transaction Count Heatmap",
             fontweight="bold")
ax.set_xlabel("Store Type")
ax.set_ylabel("Season")
plt.tight_layout()
p7 = PLOTS_DIR / "p7_season_storetype_heatmap.png"
fig.savefig(p7, dpi=FIG_DPI, bbox_inches="tight")
plt.close()
print(f"  ✔ Saved: {p7.name}")

# ── Plot 8: Discount uptake rate by Season (bar) ──────────────────────────────
fig, ax = plt.subplots(figsize=(8, 5))
bars8 = ax.bar(SEASON_ORDER,
               [season_disc.get(s, 0) for s in SEASON_ORDER],
               color=COLORS[:4], edgecolor="white", width=0.5)
ax.set_title("Discount Uptake Rate (%) by Season", fontweight="bold")
ax.set_xlabel("Season")
ax.set_ylabel("Discount Rate (%)")
ax.set_ylim(0, season_disc.max() * 1.2)
for bar in bars8:
    ax.text(bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.3,
            f"{bar.get_height():.1f}%",
            ha="center", va="bottom", fontsize=10, fontweight="bold")
sns.despine(ax=ax)
plt.tight_layout()
p8 = PLOTS_DIR / "p8_discount_uptake_by_season.png"
fig.savefig(p8, dpi=FIG_DPI, bbox_inches="tight")
plt.close()
print(f"  ✔ Saved: {p8.name}")

# ── Plot 9: Promotion revenue share by Season (stacked bar) ───────────────────
fig, ax = plt.subplots(figsize=(11, 5))
promo_season_rev.reindex(SEASON_ORDER).plot(
    kind="bar", stacked=True, ax=ax,
    color=COLORS[:len(promo_season_rev.columns)],
    edgecolor="white", linewidth=0.4, width=0.55,
)
ax.set_title("Promotion Revenue Contribution by Season (Stacked)",
             fontweight="bold")
ax.set_xlabel("Season")
ax.set_ylabel("Total Revenue ($)")
ax.set_xticklabels(SEASON_ORDER, rotation=0)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1000:.0f}k"))
ax.legend(title="Promotion Type", bbox_to_anchor=(1.01, 1),
          loc="upper left", fontsize=8, title_fontsize=8)
sns.despine(ax=ax)
plt.tight_layout()
p9 = PLOTS_DIR / "p9_promotion_revenue_by_season_stacked.png"
fig.savefig(p9, dpi=FIG_DPI, bbox_inches="tight")
plt.close()
print(f"  ✔ Saved: {p9.name}")


# =============================================================================
#  SECTION E — KEY INSIGHTS SUMMARY  (printed at the end)
# =============================================================================
print("\n" + "="*60)
print("  KEY INSIGHTS SUMMARY")
print("="*60)

print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  A. DISCOUNT vs NON-DISCOUNT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • {disc_count:,} transactions had a discount ({disc_count/total*100:.1f}% of all transactions)
  • {no_disc_count:,} transactions had no discount ({no_disc_count/total*100:.1f}%)

  • Avg spend WITH discount    : ${compare.loc['Discount Applied','Avg_Spend']:.2f}
  • Avg spend WITHOUT discount : ${compare.loc['No Discount','Avg_Spend']:.2f}
  • Spend difference           : ${spend_diff:+.2f} per transaction

  • Total revenue WITH discount    : ${compare.loc['Discount Applied','Total_Revenue']:,.2f}
  • Total revenue WITHOUT discount : ${compare.loc['No Discount','Total_Revenue']:,.2f}

  • Statistical test (Welch t-test) p-value : {p_value:.6f}
    → {'SIGNIFICANT difference in spend (p < 0.05)' if p_value < 0.05 else 'NO significant difference (p ≥ 0.05)'}

  • Highest discount users (category) : {cat_disc.idxmax()} ({cat_disc.max():.1f}%)
  • Lowest  discount users (category) : {cat_disc.idxmin()} ({cat_disc.min():.1f}%)
  • Store with highest discount rate  : {store_disc.idxmax()} ({store_disc.max():.1f}%)
  • Peak discount season              : {season_disc.idxmax()} ({season_disc.max():.1f}%)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  B. PROMOTION EFFECTIVENESS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • Highest revenue promotion  : {promo_overview['Total_Revenue'].idxmax()}
    Revenue ${promo_overview['Total_Revenue'].max():,.2f}  ({promo_overview['Revenue_Share_%'].max():.1f}% of all revenue)

  • Highest avg-spend promotion: {promo_kpi['Avg_Spend'].idxmax()}
    Avg spend ${promo_kpi['Avg_Spend'].max():.2f}

  • Largest basket promotion   : {promo_kpi['Avg_Items'].idxmax()}
    Avg {promo_kpi['Avg_Items'].max():.2f} items/transaction

  • Most-used promotion overall: {promo_overview['Transactions'].idxmax()}
    ({promo_overview['Transactions'].max():,} transactions, {promo_overview['Txn_Share_%'].max():.1f}% share)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  C. SEASONAL TRENDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • Highest revenue season : {season_kpi['Total_Revenue'].idxmax()}
    ${season_kpi['Total_Revenue'].max():,.2f}  ({season_kpi.loc[season_kpi['Total_Revenue'].idxmax(),'Transactions']:,} transactions)

  • Lowest  revenue season : {season_kpi['Total_Revenue'].idxmin()}
    ${season_kpi['Total_Revenue'].min():,.2f}  ({season_kpi.loc[season_kpi['Total_Revenue'].idxmin(),'Transactions']:,} transactions)

  • Highest avg spend season: {season_kpi['Avg_Spend'].idxmax()} (${season_kpi['Avg_Spend'].max():.2f})
  • Lowest  avg spend season: {season_kpi['Avg_Spend'].idxmin()} (${season_kpi['Avg_Spend'].min():.2f})
""")

# Per-season preferred store, payment method & dominant promo
print("  Seasonal Preferences:")
print(f"  {'Season':<10} {'Best Store Type':<22} {'Payment Method':<20} {'Dominant Promo'}")
print("  " + "-"*80)
for s in SEASON_ORDER:
    store = pref_store_season.get(s, "N/A")
    pay   = pref_pay_season.get(s, "N/A")
    promo = dominant_promo_season.get(s, "N/A")
    print(f"  {s:<10} {store:<22} {pay:<20} {promo}")

print(f"\n  All plots saved to: {PLOTS_DIR}\n")
