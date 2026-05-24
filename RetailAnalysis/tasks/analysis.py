"""
=============================================================
  Retail Transaction Data Analysis — Full Project
  Tasks 1–6: Data Prep → Exploration → Behaviour →
             Promotions → Seasonality → Visualisations
=============================================================
"""
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")          # non-interactive backend (no display needed)
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import ast
import warnings
warnings.filterwarnings("ignore")


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DATA_FILE = PROJECT_ROOT / "data" / "sample transaction.csv"
#DATA_FILE = BASE_DIR / "data" / "Retail_Transactions_Dataset-1.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
PLOTS_DIR = OUTPUT_DIR / "plots"


# ── shared style ────────────────────────────────────────────
PALETTE   = "Set2"
FIG_DPI   = 150
sns.set_theme(style="whitegrid", palette=PALETTE)
plt.rcParams.update({"axes.titlesize": 13, "axes.labelsize": 11,
                     "figure.dpi": FIG_DPI})

# ============================================================
#  TASK 1 – Data Preparation
# ============================================================
print("\n" + "="*60)
print("  TASK 1 — DATA PREPARATION")
print("="*60)

# --- 1a. Load the CSV ---
df = pd.read_csv(DATA_FILE,
                 encoding="utf-8-sig")   # handles BOM if present
print(f"\nRaw shape: {df.shape[0]} rows × {df.shape[1]} columns")
print("\nColumn dtypes (before cleaning):\n", df.dtypes)

# --- 1b. Parse Date column ---
df["Date"] = pd.to_datetime(
    df["Date"],
    format="mixed",
    dayfirst=True,   # keep only if some values are day-first
    errors="coerce"
)
bad_dates = df["Date"].isna().sum()
if bad_dates:
    print(f"Warning: {bad_dates} rows have unparseable dates.")
# --- 1c. Extract date parts ---
df["Year"]       = df["Date"].dt.year
df["Month"]      = df["Date"].dt.month
df["MonthName"]  = df["Date"].dt.strftime("%b")
df["DayOfWeek"]  = df["Date"].dt.day_name()

# --- 1d. Clean Discount_Applied (boolean) ---
df["Discount_Applied"] = df["Discount_Applied"].astype(str).str.strip().str.upper()
df["Discount_Applied"] = df["Discount_Applied"].map({"TRUE": True, "FALSE": False})

# --- 1e. Parse Product list column (stored as a Python-list string) ---
def parse_products(raw):
    """Return a clean Python list from the messy string repr."""
    try:
        return ast.literal_eval(str(raw))
    except Exception:
        return []

df["Product_List"] = df["Product"].apply(parse_products)

# --- 1f. Quick sanity check ---
print(f"\nMissing values per column:\n{df.isnull().sum()}")
print(f"\nDate range: {df['Date'].min().date()} → {df['Date'].max().date()}")
print(f"\nSample of cleaned data:")
print(df[["Transaction_ID","Date","Year","Month","DayOfWeek",
          "Total_Cost","Discount_Applied"]].head(3).to_string(index=False))


# ============================================================
#  TASK 2 – Basic Exploration
# ============================================================
print("\n" + "="*60)
print("  TASK 2 — BASIC EXPLORATION")
print("="*60)

# 2a. Total transactions
total_txn = len(df)
print(f"\n• Total transactions : {total_txn:,}")

# 2b. Unique customers
unique_customers = df["Customer_Name"].nunique()
print(f"• Unique customers   : {unique_customers:,}")

# 2c. Top-5 most common products
all_products = [p for sublist in df["Product_List"] for p in sublist]
top5_products = (pd.Series(all_products)
                 .value_counts()
                 .head(5))
print("\n• Top-5 most common products:")
print(top5_products.to_string())

# 2d. Cities with highest transaction counts
top_cities = df["City"].value_counts().head(10)
print("\n• Transaction count by city (top 10):")
print(top_cities.to_string())


# ============================================================
#  TASK 3 – Customer Behaviour Analysis
# ============================================================
print("\n" + "="*60)
print("  TASK 3 — CUSTOMER BEHAVIOUR ANALYSIS")
print("="*60)

# 3a. Average spend per customer category
avg_spend = (df.groupby("Customer_Category")["Total_Cost"]
             .mean()
             .sort_values(ascending=False)
             .round(2))
print("\n• Average spend by customer category:")
print(avg_spend.to_string())

# 3b. Preferred payment method per category (mode)
pay_pref = (df.groupby(["Customer_Category","Payment_Method"])
            .size()
            .reset_index(name="Count"))
pay_pref_pivot = pay_pref.pivot_table(index="Customer_Category",
                                       columns="Payment_Method",
                                       values="Count",
                                       fill_value=0)
print("\n• Payment method counts per customer category:")
print(pay_pref_pivot.to_string())

# 3c. Average items per transaction, per store type
avg_items_store = (df.groupby("Store_Type")["Total_Items"]
                   .mean()
                   .sort_values(ascending=False)
                   .round(2))
print("\n• Avg items per transaction by store type:")
print(avg_items_store.to_string())


# ============================================================
#  TASK 4 – Promotion & Discount Impact
# ============================================================
print("\n" + "="*60)
print("  TASK 4 — PROMOTION & DISCOUNT IMPACT")
print("="*60)

# 4a. Average cost: discount applied vs not
disc_avg = (df.groupby("Discount_Applied")["Total_Cost"]
            .agg(["mean","count"])
            .rename(columns={"mean":"Avg_Cost","count":"Transactions"})
            .round(2))
disc_avg.index = disc_avg.index.map({True:"Discount Applied",
                                     False:"No Discount"})
print("\n• Avg transaction cost — discount vs no discount:")
print(disc_avg.to_string())

# 4b. Average items per promotion type
promo_items = (df.groupby("Promotion")["Total_Items"]
               .mean()
               .sort_values(ascending=False)
               .round(2))
print("\n• Avg items purchased per promotion type:")
print(promo_items.to_string())

# 4c. Most effective promotion by average total cost
promo_cost = (df.groupby("Promotion")["Total_Cost"]
              .mean()
              .sort_values(ascending=False)
              .round(2))
print("\n• Avg total cost per promotion type:")
print(promo_cost.to_string())
print(f"\n  ➜ Most effective promotion (highest avg spend): "
      f"'{promo_cost.idxmax()}' at ${promo_cost.max():.2f}")


# ============================================================
#  TASK 5 – Seasonality Trends
# ============================================================
print("\n" + "="*60)
print("  TASK 5 — SEASONALITY TRENDS")
print("="*60)

# 5a. Total revenue per season
season_order = ["Spring","Summer","Fall","Winter"]
season_rev = (df.groupby("Season")["Total_Cost"]
              .sum()
              .reindex(season_order)
              .round(2))
print("\n• Total revenue by season:")
print(season_rev.to_string())
print(f"\n  ➜ Highest revenue season: {season_rev.idxmax()} "
      f"(${season_rev.max():,.2f})")

# 5b. Seasonal preferences — store type
season_store = (df.groupby(["Season","Store_Type"])
                .size()
                .unstack(fill_value=0)
                .reindex(season_order))
print("\n• Transaction count by season × store type:")
print(season_store.to_string())

# 5b-b. Seasonal preferences — product category (top product per season)
season_products = {}
for season in season_order:
    prods = [p for sub in df.loc[df["Season"]==season,"Product_List"]
             for p in sub]
    top = pd.Series(prods).value_counts().head(3).index.tolist()
    season_products[season] = top
print("\n• Top-3 products per season:")
for s, prods in season_products.items():
    print(f"  {s}: {', '.join(prods)}")

# 5c. Average spending per season (printed + plot generated in Task 6)
avg_season_spend = (df.groupby("Season")["Total_Cost"]
                    .mean()
                    .reindex(season_order)
                    .round(2))
print("\n• Average spend per season:")
print(avg_season_spend.to_string())


# ============================================================
#  TASK 6 – Visualisation Dashboard
# ============================================================
print("\n" + "="*60)
print("  TASK 6 — VISUALISATION DASHBOARD")
print("="*60)

from matplotlib.gridspec import GridSpec

fig = plt.figure(figsize=(22, 26))
fig.suptitle("Retail Transaction Analysis Dashboard",
             fontsize=20, fontweight="bold", y=0.995)

gs = GridSpec(4, 2, figure=fig, hspace=0.42, wspace=0.32)

# ── colours ─────────────────────────────────────────────────
COLORS = sns.color_palette(PALETTE, 12)

# ----------------------------------------------------------
# Plot 1 — Transactions per city (bar)
# ----------------------------------------------------------
ax1 = fig.add_subplot(gs[0, :])    # full top row
city_counts = df["City"].value_counts().sort_values(ascending=False)
bars = ax1.bar(city_counts.index, city_counts.values,
               color=COLORS[:len(city_counts)], edgecolor="white", linewidth=0.6)
ax1.set_title("Number of Transactions per City", fontweight="bold")
ax1.set_xlabel("City")
ax1.set_ylabel("Transaction Count")
for bar in bars:
    ax1.text(bar.get_x() + bar.get_width()/2,
             bar.get_height() + 3, str(int(bar.get_height())),
             ha="center", va="bottom", fontsize=9)
ax1.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
sns.despine(ax=ax1, left=False)

# ----------------------------------------------------------
# Plot 2 — Payment method distribution (pie)
# ----------------------------------------------------------
ax2 = fig.add_subplot(gs[1, 0])
pay_counts = df["Payment_Method"].value_counts()
wedges, texts, autotexts = ax2.pie(
    pay_counts.values,
    labels=pay_counts.index,
    autopct="%1.1f%%",
    colors=COLORS[:len(pay_counts)],
    startangle=140,
    pctdistance=0.82,
    wedgeprops={"edgecolor":"white","linewidth":1.2}
)
for t in autotexts:
    t.set_fontsize(9)
ax2.set_title("Payment Method Distribution", fontweight="bold")

# ----------------------------------------------------------
# Plot 3 — Monthly revenue trend (line, coloured by year)
# ----------------------------------------------------------
ax3 = fig.add_subplot(gs[1, 1])
monthly_rev = (df.groupby(["Year","Month"])["Total_Cost"]
               .sum()
               .reset_index())
month_labels = ["Jan","Feb","Mar","Apr","May","Jun",
                "Jul","Aug","Sep","Oct","Nov","Dec"]
for i, (yr, grp) in enumerate(monthly_rev.groupby("Year")):
    ax3.plot(grp["Month"], grp["Total_Cost"],
             marker="o", markersize=4, linewidth=1.8,
             label=str(yr), color=COLORS[i])
ax3.set_xticks(range(1, 13))
ax3.set_xticklabels(month_labels, fontsize=8)
ax3.set_title("Monthly Revenue Trend (by Year)", fontweight="bold")
ax3.set_xlabel("Month")
ax3.set_ylabel("Total Revenue ($)")
ax3.legend(title="Year", fontsize=8, title_fontsize=8)
ax3.yaxis.set_major_formatter(mticker.FuncFormatter(
    lambda x, _: f"${x/1000:.0f}k"))
sns.despine(ax=ax3, left=False)

# ----------------------------------------------------------
# Plot 4 — Revenue by season & customer category (stacked bar)
# ----------------------------------------------------------
ax4 = fig.add_subplot(gs[2, :])
rev_matrix = (df.groupby(["Season","Customer_Category"])["Total_Cost"]
              .sum()
              .unstack(fill_value=0)
              .reindex(season_order))
rev_matrix.plot(kind="bar", stacked=True, ax=ax4,
                color=COLORS[:len(rev_matrix.columns)],
                edgecolor="white", linewidth=0.4, width=0.65)
ax4.set_title("Revenue by Season & Customer Category (Stacked Bar)",
              fontweight="bold")
ax4.set_xlabel("Season")
ax4.set_ylabel("Total Revenue ($)")
ax4.set_xticklabels(season_order, rotation=0)
ax4.yaxis.set_major_formatter(mticker.FuncFormatter(
    lambda x, _: f"${x/1000:.0f}k"))
ax4.legend(title="Customer Category", bbox_to_anchor=(1.01, 1),
           loc="upper left", fontsize=8, title_fontsize=8)
sns.despine(ax=ax4, left=False)

# ----------------------------------------------------------
# Plot 5 — Avg spend per season (bonus bar from Task 5c)
# ----------------------------------------------------------
ax5 = fig.add_subplot(gs[3, 0])
bars5 = ax5.bar(avg_season_spend.index, avg_season_spend.values,
                color=COLORS[:4], edgecolor="white")
ax5.set_title("Average Spending per Season", fontweight="bold")
ax5.set_xlabel("Season")
ax5.set_ylabel("Avg Spend ($)")
for bar in bars5:
    ax5.text(bar.get_x() + bar.get_width()/2,
             bar.get_height() + 0.3,
             f"${bar.get_height():.2f}",
             ha="center", va="bottom", fontsize=9)
sns.despine(ax=ax5, left=False)

# ----------------------------------------------------------
# Plot 6 — Avg cost: Discount vs No Discount (horizontal bar)
# ----------------------------------------------------------
ax6 = fig.add_subplot(gs[3, 1])
disc_vals  = disc_avg["Avg_Cost"]
disc_cols  = [COLORS[2], COLORS[3]]
bars6 = ax6.barh(disc_vals.index, disc_vals.values,
                 color=disc_cols, edgecolor="white")
ax6.set_title("Avg Transaction Cost:\nDiscount vs No Discount",
              fontweight="bold")
ax6.set_xlabel("Avg Cost ($)")
for bar in bars6:
    ax6.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
             f"${bar.get_width():.2f}", va="center", fontsize=10)
ax6.set_xlim(0, disc_vals.max() * 1.18)
sns.despine(ax=ax6, left=False)

# ── Save ────────────────────────────────────────────────────
PLOTS_DIR.mkdir(parents=True, exist_ok=True)  # create outputs/plots if missing
out_path = PLOTS_DIR / "transaction_dashboard.png"
fig.savefig(out_path, dpi=FIG_DPI, bbox_inches="tight")
plt.close()
print(f"\nDashboard saved → {out_path}")


# ============================================================
#  KEY INSIGHTS SUMMARY
# ============================================================
print("\n" + "="*60)
print("  KEY INSIGHTS SUMMARY")
print("="*60)

print(f"""
1. DATASET OVERVIEW
   • {total_txn:,} total transactions from {df['Date'].min().year}–{df['Date'].max().year}
   • {unique_customers:,} unique customers across {df['City'].nunique()} cities

2. TOP PRODUCTS & CITIES
   • Best-selling product : {top5_products.index[0]} ({top5_products.iloc[0]:,} appearances)
   • Most active city     : {top_cities.index[0]} ({top_cities.iloc[0]:,} transactions)

3. CUSTOMER BEHAVIOUR
   • Highest-spending category : {avg_spend.index[0]} (${avg_spend.iloc[0]:.2f} avg)
   • Lowest-spending category  : {avg_spend.index[-1]} (${avg_spend.iloc[-1]:.2f} avg)
   • Store type with most items/txn: {avg_items_store.index[0]} ({avg_items_store.iloc[0]} items)

4. PROMOTIONS & DISCOUNTS
   • Transactions WITH discount avg  : ${disc_avg.loc['Discount Applied','Avg_Cost']:.2f}
   • Transactions WITHOUT discount avg: ${disc_avg.loc['No Discount','Avg_Cost']:.2f}
   • Most effective promotion type   : {promo_cost.idxmax()} (${promo_cost.max():.2f} avg spend)

5. SEASONALITY
   • Highest revenue season : {season_rev.idxmax()} (${season_rev.max():,.2f})
   • Lowest revenue season  : {season_rev.idxmin()} (${season_rev.min():,.2f})
   • Highest avg spend season: {avg_season_spend.idxmax()} (${avg_season_spend.max():.2f})
""")
