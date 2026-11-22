"""
Core reusable analysis functions for Online Shopping Behaviour and Purchase Trend Analysis.
Used across both the Jupyter Notebook (EDA_Analysis.ipynb) and interactive Streamlit web dashboard (app.py).

Implements:
- Data ingestion (CSV & Excel)
- Column type detection & intelligent auto-mapping
- Data quality reporting & cleaning
- KPI calculations
- Grouping, pivot, and percentage tables
- Bivariate analysis: contingency tables & Chi-square independence tests
- Tukey's Resistant Line (Unit 4: Median-Median robust fitting) vs OLS Regression
- Multivariate & 3-variable contingency analysis (Unit 5)
- Time-series aggregation, resampling (Daily, Weekly, Monthly, Quarterly), and moving averages
- Customer spending segmentation & payment channel analytics
"""

import os
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional, Union
from scipy import stats

def load_dataset(filepath_or_buffer: Any) -> pd.DataFrame:
    """
    Loads dataset from a file path or uploaded buffer (CSV or Excel).
    Handles encoding fallbacks and format detection.
    """
    if hasattr(filepath_or_buffer, 'name'):
        filename = filepath_or_buffer.name.lower()
    elif isinstance(filepath_or_buffer, str):
        filename = filepath_or_buffer.lower()
    else:
        filename = "uploaded_file.csv"

    if filename.endswith('.xlsx') or filename.endswith('.xls'):
        try:
            return pd.read_excel(filepath_or_buffer, engine='openpyxl')
        except Exception:
            return pd.read_excel(filepath_or_buffer)
    else:
        # Attempt standard utf-8 then fallback to latin1
        try:
            return pd.read_csv(filepath_or_buffer, encoding='utf-8')
        except UnicodeDecodeError:
            if hasattr(filepath_or_buffer, 'seek'):
                filepath_or_buffer.seek(0)
            return pd.read_csv(filepath_or_buffer, encoding='latin-1')

def detect_column_types(df: pd.DataFrame) -> Dict[str, List[str]]:
    """
    Categorizes DataFrame columns into numerical, categorical, and datetime candidate lists.
    """
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=['object', 'category', 'string']).columns.tolist()
    date_cols = []

    # Check object columns that might represent dates
    for col in cat_cols.copy():
        col_lower = col.lower()
        if any(term in col_lower for term in ['date', 'time', 'timestamp', 'day']):
            date_cols.append(col)
        else:
            # Sample check for datetime parsability
            sample = df[col].dropna().head(10)
            if not sample.empty:
                try:
                    pd.to_datetime(sample, errors='raise')
                    date_cols.append(col)
                except Exception:
                    pass

    return {
        "numerical": num_cols,
        "categorical": cat_cols,
        "datetime": date_cols,
        "all": list(df.columns)
    }

def auto_map_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """
    Heuristically matches columns in an unknown e-commerce dataset
    to standardized roles required by the EDA engine.
    """
    cols = list(df.columns)
    cols_lower = {c: c.lower().replace(" ", "_").replace("-", "_") for c in cols}

    def match_col(keywords: List[str]) -> Optional[str]:
        for original, clean in cols_lower.items():
            for kw in keywords:
                if kw in clean:
                    return original
        return None

    mapping = {
        "order_id": match_col(["order_id", "invoiceno", "invoice", "transaction_id", "order_no", "order_num"]),
        "customer_id": match_col(["customer_id", "cust_id", "user_id", "user_code", "client_id", "customer"]),
        "order_date": match_col(["order_date", "trans_date", "transaction_date", "date", "timestamp", "invoice_date"]),
        "category": match_col(["category", "department", "product_category", "item_group", "type"]),
        "product_name": match_col(["product_name", "product", "item_name", "description", "item_description", "title"]),
        "quantity": match_col(["quantity", "qty", "units", "units_purchased", "count", "items"]),
        "unit_price": match_col(["unit_price", "price", "item_rate", "rate", "cost_per_unit"]),
        "discount": match_col(["discount", "discount_rate", "markdown", "rebate"]),
        "payment_method": match_col(["payment_method", "payment", "channel", "settlement_channel", "pay_mode"]),
        "location": match_col(["location", "city", "state", "region", "country", "customer_location", "province"]),
        "total_amount": match_col(["total_amount", "total", "amount", "net_sales_value", "sales", "revenue", "spend", "net_amount"])
    }

    # Fallback heuristics for required columns if not detected
    types = detect_column_types(df)
    if not mapping["order_date"] and types["datetime"]:
        mapping["order_date"] = types["datetime"][0]
    if not mapping["category"] and types["categorical"]:
        mapping["category"] = types["categorical"][0]
    if not mapping["total_amount"] and types["numerical"]:
        # Choose numerical column with highest mean/max as amount candidate
        mapping["total_amount"] = types["numerical"][-1]
    if not mapping["quantity"] and types["numerical"]:
        for col in types["numerical"]:
            if df[col].dropna().between(1, 100).all():
                mapping["quantity"] = col
                break

    return mapping

def get_data_quality_report(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Generates a comprehensive data quality audit:
    dimensions, missing counts/percentages, duplicate rows, data types.
    """
    n_rows, n_cols = df.shape
    missing_counts = df.isnull().sum()
    missing_pct = (missing_counts / n_rows * 100).round(2)

    missing_df = pd.DataFrame({
        "Column": df.columns,
        "Data Type": df.dtypes.astype(str).values,
        "Missing Count": missing_counts.values,
        "Missing Percentage (%)": missing_pct.values
    }).sort_values(by="Missing Count", ascending=False).reset_index(drop=True)

    duplicates_count = int(df.duplicated().sum())

    return {
        "num_rows": n_rows,
        "num_cols": n_cols,
        "duplicates_count": duplicates_count,
        "duplicates_pct": round(duplicates_count / n_rows * 100, 2) if n_rows > 0 else 0.0,
        "total_missing_cells": int(missing_counts.sum()),
        "missing_table": missing_df,
        "columns": list(df.columns),
        "memory_usage_mb": round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2)
    }

def clean_data(
    df: pd.DataFrame,
    drop_duplicates: bool = True,
    fill_missing: bool = True,
    date_col: Optional[str] = None,
    amount_col: Optional[str] = None,
    qty_col: Optional[str] = None,
    unit_price_col: Optional[str] = None,
    discount_col: Optional[str] = None
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Cleans dataset:
    - Removes duplicate rows (if requested)
    - Imputes or treats missing values
    - Standardizes datetime format and extracts temporal calendar features
    - Ensures numerical validity of transaction amounts
    """
    clean_df = df.copy()
    audit: Dict[str, Any] = {
        "original_rows": len(df),
        "removed_duplicates": 0,
        "imputed_columns": []
    }

    # 1. Duplicate Removal
    if drop_duplicates:
        dups = clean_df.duplicated().sum()
        if dups > 0:
            clean_df = clean_df.drop_duplicates().reset_index(drop=True)
            audit["removed_duplicates"] = int(dups)

    # 2. Missing Value Imputation
    if fill_missing:
        for col in clean_df.columns:
            if clean_df[col].isnull().sum() > 0:
                if pd.api.types.is_numeric_dtype(clean_df[col]):
                    median_val = clean_df[col].median()
                    clean_df[col] = clean_df[col].fillna(median_val)
                    audit["imputed_columns"].append((col, f"Median ({median_val})"))
                else:
                    mode_series = clean_df[col].mode()
                    mode_val = mode_series.iloc[0] if not mode_series.empty else "Unknown"
                    clean_df[col] = clean_df[col].fillna(mode_val)
                    audit["imputed_columns"].append((col, f"Mode ('{mode_val}')"))

    # 3. Datetime Conversion & Temporal Feature Engineering
    if date_col and date_col in clean_df.columns:
        try:
            clean_df[date_col] = pd.to_datetime(clean_df[date_col], errors='coerce')
            clean_df["Year"] = clean_df[date_col].dt.year
            clean_df["Month"] = clean_df[date_col].dt.month
            clean_df["Month_Name"] = clean_df[date_col].dt.strftime("%b")
            clean_df["Month_Year"] = clean_df[date_col].dt.to_period("M").astype(str)
            clean_df["Quarter"] = clean_df[date_col].dt.to_period("Q").astype(str)
            clean_df["Day_of_Week"] = clean_df[date_col].dt.day_name()
            clean_df["Is_Weekend"] = clean_df[date_col].dt.dayofweek.isin([5, 6])
        except Exception:
            pass

    # 4. Total Amount Validation
    if amount_col and amount_col in clean_df.columns:
        clean_df[amount_col] = pd.to_numeric(clean_df[amount_col], errors='coerce')
        if clean_df[amount_col].isnull().sum() > 0:
            # If quantity, price and discount exist, recalculate missing amounts
            if qty_col and unit_price_col and qty_col in clean_df.columns and unit_price_col in clean_df.columns:
                disc = clean_df[discount_col] if (discount_col and discount_col in clean_df.columns) else 0.0
                recalc = clean_df[qty_col] * clean_df[unit_price_col] * (1.0 - disc)
                clean_df[amount_col] = clean_df[amount_col].fillna(recalc)
            clean_df[amount_col] = clean_df[amount_col].fillna(clean_df[amount_col].median())

    audit["cleaned_rows"] = len(clean_df)
    return clean_df, audit

def compute_kpis(
    df: pd.DataFrame,
    amount_col: Optional[str] = "Total Amount",
    qty_col: Optional[str] = "Quantity",
    order_id_col: Optional[str] = "Order ID",
    cust_id_col: Optional[str] = "Customer ID"
) -> Dict[str, Any]:
    """
    Computes key performance indicators from the active (or filtered) dataset.
    Dynamic: calculated directly from data with zero hardcoded values.
    """
    total_revenue = float(df[amount_col].sum()) if amount_col and amount_col in df.columns else 0.0
    total_orders = len(df)
    if order_id_col and order_id_col in df.columns:
        total_orders = int(df[order_id_col].nunique())

    total_units = int(df[qty_col].sum()) if qty_col and qty_col in df.columns else total_orders
    atv = round(total_revenue / total_orders, 2) if total_orders > 0 else 0.0
    avg_units_per_order = round(total_units / total_orders, 2) if total_orders > 0 else 0.0

    unique_customers = int(df[cust_id_col].nunique()) if cust_id_col and cust_id_col in df.columns else 0
    repeat_rate = 0.0
    if unique_customers > 0 and cust_id_col in df.columns:
        cust_counts = df[cust_id_col].value_counts()
        repeats = (cust_counts > 1).sum()
        repeat_rate = round((repeats / unique_customers) * 100, 2)

    return {
        "total_revenue": round(total_revenue, 2),
        "total_orders": total_orders,
        "total_units": total_units,
        "average_transaction_value": atv,
        "unique_customers": unique_customers,
        "avg_units_per_order": avg_units_per_order,
        "repeat_customer_rate": repeat_rate
    }

def calculate_category_summary(
    df: pd.DataFrame,
    category_col: str = "Product Category",
    amount_col: str = "Total Amount",
    qty_col: Optional[str] = "Quantity"
) -> pd.DataFrame:
    """
    Computes comprehensive category-level aggregation:
    Revenue, Order count, Units sold, Average Order Value (AOV), and Share of Revenue (%).
    """
    if category_col not in df.columns or amount_col not in df.columns:
        return pd.DataFrame()

    agg_dict = {amount_col: ["sum", "count", "mean"]}
    if qty_col and qty_col in df.columns:
        agg_dict[qty_col] = ["sum"]

    cat_df = df.groupby(category_col).agg(agg_dict)
    cat_df.columns = ["Total Revenue", "Order Count", "Average Order Value", "Total Units Sold"] if qty_col in df.columns else ["Total Revenue", "Order Count", "Average Order Value"]
    
    total_rev = cat_df["Total Revenue"].sum()
    cat_df["Revenue Share (%)"] = (cat_df["Total Revenue"] / total_rev * 100).round(2)
    cat_df = cat_df.sort_values(by="Total Revenue", ascending=False).reset_index()
    cat_df["Total Revenue"] = cat_df["Total Revenue"].round(2)
    cat_df["Average Order Value"] = cat_df["Average Order Value"].round(2)
    return cat_df

def calculate_time_series_sales(
    df: pd.DataFrame,
    date_col: str = "Order Date",
    amount_col: str = "Total Amount",
    freq: str = "ME"
) -> pd.DataFrame:
    """
    Resamples time-series transactions by frequency:
    'D' (Daily), 'W' (Weekly), 'ME' (Monthly), 'QE' (Quarterly).
    Calculates period revenue, order volume, cumulative revenue, and rolling moving averages.
    """
    if date_col not in df.columns or amount_col not in df.columns:
        return pd.DataFrame()

    temp_df = df[[date_col, amount_col]].dropna().copy()
    temp_df[date_col] = pd.to_datetime(temp_df[date_col], errors='coerce')
    temp_df = temp_df.dropna(subset=[date_col]).sort_values(date_col)

    # Convert freq aliases to pandas 2.2+ standards if needed
    freq_map = {'M': 'ME', 'Q': 'QE', 'W': 'W', 'D': 'D'}
    clean_freq = freq_map.get(freq, freq)

    ts = temp_df.set_index(date_col).resample(clean_freq)[amount_col].agg(['sum', 'count']).reset_index()
    ts.columns = ['Period', 'Revenue', 'Orders']
    ts['Revenue'] = ts['Revenue'].round(2)
    ts['Cumulative Revenue'] = ts['Revenue'].cumsum().round(2)
    ts['Moving Avg (3-Period)'] = ts['Revenue'].rolling(window=3, min_periods=1).mean().round(2)
    ts['Growth Rate (%)'] = (ts['Revenue'].pct_change() * 100).round(2).fillna(0.0)

    # Format period label for display
    if clean_freq in ['ME', 'M']:
        ts['Period_Label'] = ts['Period'].dt.strftime('%b %Y')
    elif clean_freq in ['QE', 'Q']:
        ts['Period_Label'] = ts['Period'].dt.to_period('Q').astype(str)
    elif clean_freq in ['W']:
        ts['Period_Label'] = ts['Period'].dt.strftime('%Y-W%U')
    else:
        ts['Period_Label'] = ts['Period'].dt.strftime('%Y-%m-%d')

    return ts

def calculate_contingency_table(
    df: pd.DataFrame,
    row_col: str,
    col_col: str,
    normalize: Optional[Union[str, bool]] = False,
    margins: bool = True
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Unit 4 Requirement:
    Generates Two-Variable Contingency Tables (Cross-tabulation).
    Supports frequency counts and percentage tables:
    normalize = False or None -> frequencies
    normalize = 'all' -> percentage of total
    normalize = 'index' -> row-wise percentages
    normalize = 'columns' -> column-wise percentages

    Also performs Pearson's Chi-Square Test of Independence.
    """
    if row_col not in df.columns or col_col not in df.columns:
        return pd.DataFrame(), {}

    norm_arg = normalize if normalize not in [None, False] else False

    # Contingency table
    ctable = pd.crosstab(df[row_col], df[col_col], normalize=norm_arg, margins=margins)
    if norm_arg:
        ctable = (ctable * 100).round(2)

    # Statistical test on raw counts
    raw_ctable = pd.crosstab(df[row_col], df[col_col], normalize=False)
    stat_report = {}
    try:
        chi2, p_val, dof, expected = stats.chi2_contingency(raw_ctable)
        stat_report = {
            "chi2_statistic": round(float(chi2), 3),
            "p_value": float(p_val),
            "degrees_of_freedom": int(dof),
            "is_significant_05": bool(p_val < 0.05),
            "interpretation": (
                f"Statistically significant association exists between {row_col} and {col_col} (p = {p_val:.4e} < 0.05)."
                if p_val < 0.05 else
                f"No statistically significant association observed between {row_col} and {col_col} (p = {p_val:.4e} >= 0.05)."
            )
        }
    except Exception as e:
        stat_report = {"error": str(e)}

    return ctable, stat_report

def calculate_three_variable_contingency(
    df: pd.DataFrame,
    row_col: str,
    col_col: str,
    layer_col: str,
    normalize: Optional[Union[str, bool]] = False
) -> pd.DataFrame:
    """
    Unit 5 Requirement:
    Three-Variable Contingency Table (introducing a third conditioning variable / layer).
    Cross-tabulates row_col and col_col across each level of layer_col.
    """
    if not all(col in df.columns for col in [row_col, col_col, layer_col]):
        return pd.DataFrame()

    norm_arg = normalize if normalize not in [None, False] else False

    crosstab_3v = pd.crosstab(
        index=[df[layer_col], df[row_col]],
        columns=df[col_col],
        normalize=norm_arg,
        margins=False
    )
    if norm_arg:
        crosstab_3v = (crosstab_3v * 100).round(2)
    return crosstab_3v

def calculate_resistant_line(
    x_series: pd.Series,
    y_series: pd.Series
) -> Dict[str, Any]:
    """
    Unit 4 Requirement:
    Tukey's Resistant Line (Median-Median Robust Line Fitting).
    Unlike Ordinary Least Squares (OLS) which minimizes squared residuals and is highly sensitive
    to extreme outliers, Tukey's resistant line divides sorted data into three equal batches (Left, Middle, Right),
    determines the median coordinate for each batch, and computes slope and intercept resistant to anomalous points.

    Algorithm:
    1. Sort data by X.
    2. Partition into 3 groups of size n/3 (Left, Middle, Right).
    3. Calculate summary medians: (x_L, y_L), (x_M, y_M), (x_R, y_R).
    4. Slope b = (y_R - y_L) / (x_R - x_L).
    5. Intercept a = (1/3) * [ (y_L - b*x_L) + (y_M - b*x_M) + (y_R - b*x_R) ].
    """
    clean_pair = pd.DataFrame({"x": x_series, "y": y_series}).dropna()
    clean_pair = clean_pair.sort_values(by="x").reset_index(drop=True)
    n = len(clean_pair)

    if n < 6:
        return {"error": "Need at least 6 observations for 3-group resistant line."}

    # Partition sizes: n = 3*q + r
    q, r = divmod(n, 3)
    if r == 0:
        n_L, n_M, n_R = q, q, q
    elif r == 1:
        n_L, n_M, n_R = q, q + 1, q
    else:  # r == 2
        n_L, n_M, n_R = q + 1, q, q + 1

    group_L = clean_pair.iloc[:n_L]
    group_M = clean_pair.iloc[n_L:n_L + n_M]
    group_R = clean_pair.iloc[n_L + n_M:]

    # Median summary points
    x_L, y_L = float(group_L["x"].median()), float(group_L["y"].median())
    x_M, y_M = float(group_M["x"].median()), float(group_M["y"].median())
    x_R, y_R = float(group_R["x"].median()), float(group_R["y"].median())

    if x_R == x_L:
        b = 0.0
    else:
        b = (y_R - y_L) / (x_R - x_L)

    # Intercept balancing all three medians
    a = (1.0 / 3.0) * ((y_L - b * x_L) + (y_M - b * x_M) + (y_R - b * x_R))

    # Fitted values and robust residuals
    fitted = a + b * clean_pair["x"]
    residuals = clean_pair["y"] - fitted
    mad_res = float(np.median(np.abs(residuals - np.median(residuals))))

    return {
        "slope": round(float(b), 4),
        "intercept": round(float(a), 4),
        "equation": f"y = {a:.2f} + {b:.2f}x",
        "medians": {
            "Left": (round(x_L, 2), round(y_L, 2)),
            "Middle": (round(x_M, 2), round(y_M, 2)),
            "Right": (round(x_R, 2), round(y_R, 2))
        },
        "median_absolute_residual": round(mad_res, 3),
        "x_sorted": clean_pair["x"].values,
        "y_fitted": fitted.values,
        "group_sizes": (n_L, n_M, n_R)
    }

def calculate_ols_line(x_series: pd.Series, y_series: pd.Series) -> Dict[str, Any]:
    """
    Standard Ordinary Least Squares (OLS) Linear Regression.
    Returns slope, intercept, R-squared, and standard error for comparison against Tukey's resistant line.
    """
    clean_pair = pd.DataFrame({"x": x_series, "y": y_series}).dropna()
    if len(clean_pair) < 2:
        return {"error": "Insufficient data for OLS."}

    slope, intercept, r_val, p_val, std_err = stats.linregress(clean_pair["x"], clean_pair["y"])
    return {
        "slope": round(float(slope), 4),
        "intercept": round(float(intercept), 4),
        "r_squared": round(float(r_val ** 2), 4),
        "p_value": float(p_val),
        "std_err": round(float(std_err), 4),
        "equation": f"y = {intercept:.2f} + {slope:.2f}x"
    }

def calculate_correlation_matrix(
    df: pd.DataFrame,
    numeric_cols: Optional[List[str]] = None,
    method: str = "pearson"
) -> pd.DataFrame:
    """
    Calculates Pearson, Spearman, or Kendall correlation matrix for numerical features.
    """
    if numeric_cols is None:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    else:
        numeric_cols = [c for c in numeric_cols if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]

    if not numeric_cols:
        return pd.DataFrame()

    return df[numeric_cols].corr(method=method).round(3)

def customer_spending_analysis(
    df: pd.DataFrame,
    cust_id_col: str = "Customer ID",
    amount_col: str = "Total Amount",
    order_id_col: Optional[str] = "Order ID"
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Performs customer-level behavior analysis:
    - Customer lifetime spend, order frequency, average basket size
    - Segmentation into spending quartiles (Bronze, Silver, Gold, Platinum)
    """
    if cust_id_col not in df.columns or amount_col not in df.columns:
        return pd.DataFrame(), {}

    agg_spec = {amount_col: ["sum", "mean", "count"]}
    cust_df = df.groupby(cust_id_col).agg(agg_spec)
    cust_df.columns = ["Total Spend", "Avg Order Value", "Order Frequency"]
    cust_df = cust_df.round(2)

    # Segment customers by spend quartiles
    try:
        cust_df["Tier"] = pd.qcut(
            cust_df["Total Spend"],
            q=4,
            labels=["Bronze (Low)", "Silver (Mid)", "Gold (High)", "Platinum (Top)"]
        )
    except Exception:
        cust_df["Tier"] = "Standard"

    cust_df = cust_df.sort_values(by="Total Spend", ascending=False).reset_index()

    summary = {
        "total_unique_customers": len(cust_df),
        "mean_customer_spend": round(cust_df["Total Spend"].mean(), 2),
        "median_customer_spend": round(cust_df["Total Spend"].median(), 2),
        "max_customer_spend": round(cust_df["Total Spend"].max(), 2),
        "repeat_buyers_count": int((cust_df["Order Frequency"] > 1).sum()),
        "single_order_buyers_count": int((cust_df["Order Frequency"] == 1).sum())
    }

    return cust_df, summary

def payment_distribution_analysis(
    df: pd.DataFrame,
    payment_col: str = "Payment Method",
    amount_col: str = "Total Amount"
) -> pd.DataFrame:
    """
    Analyzes payment channel adoption:
    Transaction count, volume share (%), total revenue, and average transaction amount.
    """
    if payment_col not in df.columns or amount_col not in df.columns:
        return pd.DataFrame()

    pay_summary = df.groupby(payment_col).agg(
        Order_Count=(amount_col, "count"),
        Total_Revenue=(amount_col, "sum"),
        Average_Order_Value=(amount_col, "mean")
    ).reset_index()

    total_orders = pay_summary["Order_Count"].sum()
    total_rev = pay_summary["Total_Revenue"].sum()

    pay_summary["Order Share (%)"] = (pay_summary["Order_Count"] / total_orders * 100).round(2)
    pay_summary["Revenue Share (%)"] = (pay_summary["Total_Revenue"] / total_rev * 100).round(2)
    pay_summary["Total_Revenue"] = pay_summary["Total_Revenue"].round(2)
    pay_summary["Average_Order_Value"] = pay_summary["Average_Order_Value"].round(2)
    pay_summary = pay_summary.sort_values(by="Total_Revenue", ascending=False).reset_index(drop=True)

    return pay_summary
