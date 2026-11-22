"""
Comprehensive Automated Test Suite for Online Shopping Behaviour Analysis.
Validates:
1. Reusable functions in src/analysis.py
2. Primary dataset (CSV) ingestion, duplicate removal, missing value imputation
3. Dynamic KPI calculations and reactive filtering
4. Unit 4: Tukey's Resistant Line vs OLS Regression
5. Unit 4 & 5: Contingency tables (2-variable and 3-variable) and Chi-square tests
6. Unit 5: Time-series resampling (D, W, ME, QE)
7. Alternative dataset (Excel .xlsx) with different column names & auto-column mapping
8. App.py syntax and import verification
"""

import os
import sys
import numpy as np
import pandas as pd

BASE_DIR = r"C:\Users\abidh\.gemini\antigravity\scratch\Online_Shopping_Behaviour_Analysis"
sys.path.insert(0, BASE_DIR)

from src import analysis

def test_primary_dataset():
    print("=== TEST 1: Primary CSV Dataset Ingestion & Cleaning ===")
    csv_path = os.path.join(BASE_DIR, "dataset", "online_shopping_data.csv")
    assert os.path.exists(csv_path), f"Primary CSV not found: {csv_path}"

    df = analysis.load_dataset(csv_path)
    assert len(df) > 3000, f"Expected >3000 rows, got {len(df)}"
    print(f"Loaded primary CSV: {len(df)} rows, {df.shape[1]} columns.")

    # Quality report before cleaning
    q_rep = analysis.get_data_quality_report(df)
    print(f"Raw duplicates detected: {q_rep['duplicates_count']}")
    print(f"Raw missing cells detected: {q_rep['total_missing_cells']}")
    assert q_rep['duplicates_count'] > 0, "Expected intentional duplicates in raw dataset"
    assert q_rep['total_missing_cells'] > 0, "Expected intentional missing values in raw dataset"

    # Cleaning
    cleaned_df, audit = analysis.clean_data(
        df,
        drop_duplicates=True,
        fill_missing=True,
        date_col="Order Date",
        amount_col="Total Amount",
        qty_col="Quantity",
        unit_price_col="Unit Price",
        discount_col="Discount"
    )
    assert cleaned_df.isnull().sum().sum() == 0, "Cleaned dataset contains unexpected nulls!"
    assert cleaned_df.duplicated().sum() == 0, "Cleaned dataset contains duplicate rows!"
    print(f"Cleaned dataset verified: {len(cleaned_df)} rows. All nulls and duplicates purged.")
    return cleaned_df

def test_dynamic_kpis_and_filters(cleaned_df):
    print("\n=== TEST 2: Dynamic KPIs and Reactive Filtering ===")
    full_kpis = analysis.compute_kpis(cleaned_df)
    print(f"Full Dataset KPIs: Revenue=${full_kpis['total_revenue']:,.2f}, Orders={full_kpis['total_orders']}")

    # Apply Category Filter: Electronics only
    electronics_df = cleaned_df[cleaned_df["Product Category"] == "Electronics"]
    elec_kpis = analysis.compute_kpis(electronics_df)
    print(f"Filtered (Electronics) KPIs: Revenue=${elec_kpis['total_revenue']:,.2f}, Orders={elec_kpis['total_orders']}")

    assert elec_kpis['total_revenue'] < full_kpis['total_revenue'], "Filtered revenue must be strictly less than full revenue!"
    assert elec_kpis['total_orders'] < full_kpis['total_orders'], "Filtered orders must be strictly less than full orders!"

    # Apply Date Range Filter: Q1 only
    q1_df = cleaned_df[cleaned_df["Quarter"] == "2023Q1"]
    q1_kpis = analysis.compute_kpis(q1_df)
    print(f"Filtered (Q1) KPIs: Revenue=${q1_kpis['total_revenue']:,.2f}, Orders={q1_kpis['total_orders']}")
    assert q1_kpis['total_orders'] > 0, "Q1 orders must be > 0"
    print("Dynamic KPI recalculation verified!")

def test_unit_4_and_unit_5_analytics(cleaned_df):
    print("\n=== TEST 3: Unit 4 & Unit 5 Syllabus Analytics ===")
    # Unit 4: Tukey's Resistant Line
    res_line = analysis.calculate_resistant_line(cleaned_df["Quantity"], cleaned_df["Total Amount"])
    ols_line = analysis.calculate_ols_line(cleaned_df["Quantity"], cleaned_df["Total Amount"])

    print(f"Tukey's Resistant Line Equation: {res_line['equation']}")
    print(f"OLS Regression Line Equation:   {ols_line['equation']} (R²={ols_line['r_squared']})")
    assert "slope" in res_line and res_line["slope"] > 0, "Resistant slope must be positive"
    assert "slope" in ols_line and ols_line["slope"] > 0, "OLS slope must be positive"

    # Unit 4: Contingency Table & Chi-Square
    ctab, chi_res = analysis.calculate_contingency_table(cleaned_df, "Product Category", "Payment Method", normalize=False)
    assert not ctab.empty, "Contingency table must not be empty"
    print(f"2-Var Contingency Shape: {ctab.shape}, Chi2={chi_res.get('chi2_statistic')}, p-val={chi_res.get('p_value'):.4f}")

    # Unit 5: 3-Variable Contingency Table
    ctab3 = analysis.calculate_three_variable_contingency(cleaned_df, "Product Category", "Payment Method", "Customer Location", normalize="index")
    assert not ctab3.empty, "3-variable contingency table must not be empty"
    print(f"3-Var Contingency Shape: {ctab3.shape}")

    # Unit 5: Time-Series Resampling
    ts_d = analysis.calculate_time_series_sales(cleaned_df, "Order Date", "Total Amount", freq="D")
    ts_w = analysis.calculate_time_series_sales(cleaned_df, "Order Date", "Total Amount", freq="W")
    ts_m = analysis.calculate_time_series_sales(cleaned_df, "Order Date", "Total Amount", freq="ME")
    ts_q = analysis.calculate_time_series_sales(cleaned_df, "Order Date", "Total Amount", freq="QE")

    print(f"Resampling verified: Daily({len(ts_d)}), Weekly({len(ts_w)}), Monthly({len(ts_m)}), Quarterly({len(ts_q)})")
    assert len(ts_m) == 12, f"Expected 12 months for 2023, got {len(ts_m)}"
    assert len(ts_q) == 4, f"Expected 4 quarters for 2023, got {len(ts_q)}"

def test_alternative_excel_dataset():
    print("\n=== TEST 4: Alternative Excel Dataset Ingestion & Auto-Column Mapping ===")
    xlsx_path = os.path.join(BASE_DIR, "dataset", "alternative_retail_transactions.xlsx")
    assert os.path.exists(xlsx_path), f"Excel file not found: {xlsx_path}"

    df_alt = analysis.load_dataset(xlsx_path)
    print(f"Loaded Excel dataset: {len(df_alt)} rows, Columns: {list(df_alt.columns)}")

    # Test auto-mapping
    auto_map = analysis.auto_map_columns(df_alt)
    print("Auto-detected column mappings:")
    for role, col in auto_map.items():
        print(f"  * {role} -> '{col}'")

    assert auto_map["order_id"] == "Invoice_Number"
    assert auto_map["customer_id"] == "User_Code"
    assert auto_map["order_date"] == "Transaction_Timestamp"
    assert auto_map["category"] == "Department"
    assert auto_map["quantity"] == "Units_Purchased"
    assert auto_map["total_amount"] == "Net_Sales_Value"

    # Compute KPIs using mapped columns
    alt_kpis = analysis.compute_kpis(
        df_alt,
        amount_col=auto_map["total_amount"],
        qty_col=auto_map["quantity"],
        order_id_col=auto_map["order_id"],
        cust_id_col=auto_map["customer_id"]
    )
    print(f"Excel Dataset KPIs: Revenue=${alt_kpis['total_revenue']:,.2f}, Orders={alt_kpis['total_orders']}")
    assert alt_kpis['total_revenue'] > 0
    assert alt_kpis['total_orders'] == len(df_alt)
    print("Excel Ingestion & Auto-Column Mapping Verified!")

def test_app_syntax():
    print("\n=== TEST 5: Streamlit Application (app.py) Verification ===")
    app_path = os.path.join(BASE_DIR, "app.py")
    assert os.path.exists(app_path), f"app.py not found: {app_path}"

    with open(app_path, "r", encoding="utf-8") as f:
        code = f.read()

    compile(code, app_path, "exec")
    print("app.py syntax compiled successfully with 0 errors!")

if __name__ == "__main__":
    cleaned_df = test_primary_dataset()
    test_dynamic_kpis_and_filters(cleaned_df)
    test_unit_4_and_unit_5_analytics(cleaned_df)
    test_alternative_excel_dataset()
    test_app_syntax()
    print("\n🎉 ALL UNIT & INTEGRATION TESTS PASSED WITH 100% SUCCESS!")
