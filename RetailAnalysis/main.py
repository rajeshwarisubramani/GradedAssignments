from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


# Use a non-interactive backend so plots can be created in any environment.
matplotlib.use("Agg")

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "sample transaction.csv"
#DATA_FILE = BASE_DIR / "data" / "Retail_Transactions_Dataset-1.csv"
OUTPUT_DIR = BASE_DIR / "outputs"
PLOTS_DIR = OUTPUT_DIR / "plots"


def ensure_output_dirs() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    PLOTS_DIR.mkdir(exist_ok=True)


def load_dataset(file_path: Path) -> pd.DataFrame:
    return pd.read_csv(file_path)


def inspect_dataset(df: pd.DataFrame) -> None:
    dtypes = pd.DataFrame({"column": df.columns, "dtype": df.dtypes.astype(str).values})
    missing = (
        df.isna().sum().rename("missing_count").reset_index().rename(columns={"index": "column"})
    )
    describe_numeric = df.describe(include="number").transpose()

    dtypes.to_csv(OUTPUT_DIR / "columns_and_dtypes.csv", index=False)
    missing.to_csv(OUTPUT_DIR / "missing_values.csv", index=False)
    describe_numeric.to_csv(OUTPUT_DIR / "numeric_summary.csv")

    print("Dataset shape:", df.shape)
    print("\nColumns and dtypes:")
    print(dtypes.to_string(index=False))


def clean_transform_data(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()

    cleaned["Date"] = pd.to_datetime(cleaned["Date"], dayfirst=True, errors="coerce")
    cleaned["Total_Items"] = pd.to_numeric(cleaned["Total_Items"], errors="coerce")
    cleaned["Total_Cost"] = pd.to_numeric(cleaned["Total_Cost"], errors="coerce")

    cleaned["Discount_Applied"] = (
        cleaned["Discount_Applied"].astype(str).str.upper().map({"TRUE": True, "FALSE": False})
    )

    cleaned["Promotion"] = cleaned["Promotion"].fillna("None")
    cleaned = cleaned.dropna(subset=["Date", "Total_Cost", "Total_Items"])

    cleaned["YearMonth"] = cleaned["Date"].dt.to_period("M").astype(str)
    cleaned["Month"] = cleaned["Date"].dt.month_name()
    cleaned["Weekday"] = cleaned["Date"].dt.day_name()

    return cleaned


def create_core_aggregations(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    city_transactions = (
        df.groupby("City", as_index=False)
        .agg(
            transactions=("Transaction_ID", "count"),
            total_revenue=("Total_Cost", "sum"),
            avg_transaction_value=("Total_Cost", "mean"),
        )
        .sort_values("transactions", ascending=False)
    )

    payment_distribution = (
        df.groupby("Payment_Method", as_index=False)
        .agg(transactions=("Transaction_ID", "count"), total_revenue=("Total_Cost", "sum"))
        .sort_values("transactions", ascending=False)
    )
    payment_distribution["transaction_share_pct"] = (
        payment_distribution["transactions"] / payment_distribution["transactions"].sum() * 100
    ).round(2)

    monthly_revenue = (
        df.groupby("YearMonth", as_index=False)
        .agg(transactions=("Transaction_ID", "count"), total_revenue=("Total_Cost", "sum"))
        .sort_values("YearMonth")
    )

    store_type_revenue = (
        df.groupby("Store_Type", as_index=False)
        .agg(transactions=("Transaction_ID", "count"), total_revenue=("Total_Cost", "sum"))
        .sort_values("total_revenue", ascending=False)
    )

    store_discount_performance = (
        df.groupby(["Store_Type", "Discount_Applied"], as_index=False)
        .agg(
            transactions=("Transaction_ID", "count"),
            total_revenue=("Total_Cost", "sum"),
            avg_transaction_value=("Total_Cost", "mean"),
        )
        .sort_values(["Store_Type", "Discount_Applied"])
    )

    promotion_performance = (
        df.groupby("Promotion", as_index=False)
        .agg(
            transactions=("Transaction_ID", "count"),
            total_revenue=("Total_Cost", "sum"),
            avg_transaction_value=("Total_Cost", "mean"),
        )
        .sort_values("total_revenue", ascending=False)
    )

    season_order = ["Winter", "Spring", "Summer", "Autumn"]
    store_type_season_revenue = (
        df.groupby(["Store_Type", "Season"], as_index=False)
        .agg(
            transactions=("Transaction_ID", "count"),
            total_revenue=("Total_Cost", "sum"),
            avg_transaction_value=("Total_Cost", "mean"),
        )
        .assign(Season=lambda x: pd.Categorical(x["Season"], categories=season_order, ordered=True))
        .sort_values(["Store_Type", "Season"])
    )

    category_spend = (
        df.groupby("Customer_Category", as_index=False)
        .agg(
            transactions=("Transaction_ID", "count"),
            total_revenue=("Total_Cost", "sum"),
            avg_transaction_value=("Total_Cost", "mean"),
        )
        .sort_values("total_revenue", ascending=False)
    )

    month_order = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    seasonality = (
        df.groupby("Month", as_index=False)
        .agg(transactions=("Transaction_ID", "count"), total_revenue=("Total_Cost", "sum"))
        .assign(Month=lambda x: pd.Categorical(x["Month"], categories=month_order, ordered=True))
        .sort_values("Month")
    )

    q1 = df["Total_Cost"].quantile(0.25)
    q3 = df["Total_Cost"].quantile(0.75)
    iqr = q3 - q1
    upper_fence = q3 + 1.5 * iqr
    anomalies = df[df["Total_Cost"] > upper_fence].sort_values("Total_Cost", ascending=False)

    return {
        "city_transactions": city_transactions,
        "payment_distribution": payment_distribution,
        "monthly_revenue": monthly_revenue,
        "store_type_revenue": store_type_revenue,
        "store_discount_performance": store_discount_performance,
        "store_type_season_revenue": store_type_season_revenue,
        "promotion_performance": promotion_performance,
        "category_spend": category_spend,
        "seasonality": seasonality,
        "anomalies": anomalies,
    }


def save_aggregations(aggregations: dict[str, pd.DataFrame]) -> None:
    for name, data in aggregations.items():
        data.to_csv(OUTPUT_DIR / f"{name}.csv", index=False)


def create_plots(aggregations: dict[str, pd.DataFrame], cleaned_df: pd.DataFrame) -> None:
    sns.set_theme(style="whitegrid")

    city_df = aggregations["city_transactions"]
    plt.figure(figsize=(10, 6))
    sns.barplot(data=city_df, x="City", y="transactions", color="#4C72B0")
    plt.title("Transactions by City")
    plt.xlabel("City")
    plt.ylabel("Number of Transactions")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "transactions_by_city.png", dpi=150)
    plt.close()

    payment_df = aggregations["payment_distribution"]
    plt.figure(figsize=(8, 6))
    sns.barplot(data=payment_df, x="Payment_Method", y="transactions", color="#55A868")
    plt.title("Payment Method Distribution")
    plt.xlabel("Payment Method")
    plt.ylabel("Number of Transactions")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "payment_distribution.png", dpi=150)
    plt.close()

    monthly_df = aggregations["monthly_revenue"]
    plt.figure(figsize=(12, 6))
    sns.lineplot(data=monthly_df, x="YearMonth", y="total_revenue", marker="o", color="#C44E52")
    plt.title("Monthly Revenue Trend")
    plt.xlabel("Year-Month")
    plt.ylabel("Total Revenue")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "monthly_revenue_trend.png", dpi=150)
    plt.close()

    store_df = aggregations["store_type_revenue"]
    plt.figure(figsize=(10, 6))
    sns.barplot(data=store_df, y="Store_Type", x="total_revenue", color="#8172B2")
    plt.title("Revenue by Store Type")
    plt.xlabel("Total Revenue")
    plt.ylabel("Store Type")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "revenue_by_store_type.png", dpi=150)
    plt.close()

    store_discount_df = aggregations["store_discount_performance"].copy()
    store_discount_df["Discount_Label"] = store_discount_df["Discount_Applied"].map(
        {True: "Discount Applied", False: "No Discount"}
    )
    plt.figure(figsize=(12, 6))
    sns.barplot(
        data=store_discount_df,
        x="Store_Type",
        y="total_revenue",
        hue="Discount_Label",
        palette="Set2",
    )
    plt.title("Revenue by Store Type and Discount Applied")
    plt.xlabel("Store Type")
    plt.ylabel("Total Revenue")
    plt.xticks(rotation=25, ha="right")
    plt.legend(title="Discount Status")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "store_discount_revenue_by_store_type.png", dpi=150)
    plt.close()

    # Bubble scatter: x=store type, y=discount state, size=transactions, color=revenue.
    store_discount_scatter = aggregations["store_discount_performance"].copy()
    store_discount_scatter["Discount_Flag"] = store_discount_scatter["Discount_Applied"].map(
        {False: 0, True: 1}
    )
    plt.figure(figsize=(12, 6))
    sns.scatterplot(
        data=store_discount_scatter,
        x="Store_Type",
        y="Discount_Flag",
        size="transactions",
        hue="total_revenue",
        palette="viridis",
        sizes=(120, 800),
        alpha=0.85,
        legend="brief",
    )
    plt.title("Store Type vs Discount Applied (Bubble Scatter)")
    plt.xlabel("Store Type")
    plt.ylabel("Discount Applied")
    plt.yticks([0, 1], ["No", "Yes"])
    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "storetype_discount_scatter.png", dpi=150)
    plt.close()

    promo_store_scatter = (
        cleaned_df.groupby(["Store_Type", "Promotion"], as_index=False)
        .agg(
            transactions=("Transaction_ID", "count"),
            total_revenue=("Total_Cost", "sum"),
        )
        .sort_values(["Store_Type", "Promotion"])
    )
    plt.figure(figsize=(12, 6))
    sns.scatterplot(
        data=promo_store_scatter,
        x="Store_Type",
        y="Promotion",
        size="transactions",
        hue="total_revenue",
        palette="magma",
        sizes=(120, 900),
        alpha=0.85,
        legend="brief",
    )
    plt.title("Promotion vs Store Type (Bubble Scatter)")
    plt.xlabel("Store Type")
    plt.ylabel("Promotion")
    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "promotion_store_type_scatter.png", dpi=150)
    plt.close()

    store_type_season_df = aggregations["store_type_season_revenue"]
    plt.figure(figsize=(12, 6))
    sns.barplot(
        data=store_type_season_df,
        x="Store_Type",
        y="total_revenue",
        hue="Season",
        palette="Set3",
    )
    plt.title("Revenue by Store Type and Season")
    plt.xlabel("Store Type")
    plt.ylabel("Total Revenue")
    plt.xticks(rotation=25, ha="right")
    plt.legend(title="Season")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "revenue_by_store_type_and_season.png", dpi=150)
    plt.close()


def build_observations(aggregations: dict[str, pd.DataFrame], cleaned_df: pd.DataFrame) -> list[str]:
    observations: list[str] = []

    city_df = aggregations["city_transactions"]
    top_city = city_df.iloc[0]
    city_share = top_city["transactions"] / city_df["transactions"].sum() * 100
    observations.append(
        f"Transactions by city: {top_city['City']} leads with {int(top_city['transactions'])} transactions ({city_share:.1f}% share)."
    )

    payment_df = aggregations["payment_distribution"]
    top_payment = payment_df.iloc[0]
    observations.append(
        f"Payment distribution: {top_payment['Payment_Method']} is most used at {top_payment['transaction_share_pct']:.1f}% of transactions."
    )

    monthly_df = aggregations["monthly_revenue"]
    peak_month = monthly_df.loc[monthly_df["total_revenue"].idxmax()]
    observations.append(
        f"Revenue trends: Peak monthly revenue appears in {peak_month['YearMonth']} with total revenue {peak_month['total_revenue']:.2f}."
    )

    store_df = aggregations["store_type_revenue"]
    top_store = store_df.iloc[0]
    observations.append(
        f"Store type revenue: {top_store['Store_Type']} leads with total revenue {top_store['total_revenue']:.2f}."
    )

    store_discount_df = aggregations["store_discount_performance"]
    top_discount_store = store_discount_df.loc[store_discount_df["total_revenue"].idxmax()]
    discount_status = "with discounts" if bool(top_discount_store["Discount_Applied"]) else "without discounts"
    observations.append(
        f"Store vs discount: {top_discount_store['Store_Type']} performs best {discount_status} (revenue {top_discount_store['total_revenue']:.2f})."
    )

    seasonality_df = aggregations["seasonality"]
    top_seasonal_month = seasonality_df.loc[seasonality_df["total_revenue"].idxmax()]
    observations.append(
        f"Seasonality signal: {top_seasonal_month['Month']} records the highest revenue among calendar months."
    )

    anomalies_df = aggregations["anomalies"]
    anomaly_rate = (len(anomalies_df) / len(cleaned_df)) * 100
    observations.append(
        f"Anomalies: {len(anomalies_df)} high-value transactions were flagged using IQR ({anomaly_rate:.1f}% of all transactions)."
    )

    promotion_df = aggregations["promotion_performance"]
    best_promo = promotion_df.iloc[0]
    observations.append(
        f"Promotions: {best_promo['Promotion']} contributes the most revenue overall ({best_promo['total_revenue']:.2f})."
    )

    category_df = aggregations["category_spend"]
    top_category = category_df.iloc[0]
    observations.append(
        f"Customer behavior: {top_category['Customer_Category']} customers generate the highest total spend in the dataset."
    )

    return observations


def save_insights(observations: list[str], anomaly_count: int) -> None:
    anomaly_finding = (
        "- A small set of high-value outliers exists and should be tracked separately for VIP behavior or fraud checks."
        if anomaly_count > 0
        else "- Transaction values are tightly distributed, with no high-value outliers flagged by the IQR rule."
    )

    lines = [
        "# Retail Transaction Analysis Insights",
        "",
        "## One-line observations from visuals and trends",
    ]
    lines.extend([f"- {obs}" for obs in observations])

    lines.extend(
        [
            "",
            "## Overall findings",
            "- Spending is concentrated in specific cities and customer segments, indicating uneven demand across locations.",
            "- Payment preferences are skewed toward one method, which can inform checkout optimization and targeted offers.",
            "- Revenue varies by month, suggesting seasonal timing should guide promotion calendars and inventory planning.",
            anomaly_finding,
        ]
    )

    (OUTPUT_DIR / "insights.md").write_text("\n".join(lines), encoding="utf-8")


def analysis() -> None:
    ensure_output_dirs()

    raw_df = load_dataset(DATA_FILE)
    inspect_dataset(raw_df)
    cleaned_df = clean_transform_data(raw_df)

    aggregations = create_core_aggregations(cleaned_df)
    save_aggregations(aggregations)
    create_plots(aggregations, cleaned_df)

    observations = build_observations(aggregations, cleaned_df)
    save_insights(observations, anomaly_count=len(aggregations["anomalies"]))

    print("\nAnalysis complete.")
    print(f"Artifacts saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    analysis()

