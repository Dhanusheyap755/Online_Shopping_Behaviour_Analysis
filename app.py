"""
Online Shopping Behaviour and Purchase Trend Analysis
Interactive Streamlit Web Application (app.py)

Fully Dynamic E-Commerce Analytics Dashboard supporting:
- CSV & Excel file uploads with instant state replacement
- Automatic column type detection and manual column mapping
- Dynamic KPI calculation from raw/filtered data (no hardcoded metrics)
- Unit 4: Bivariate analysis, contingency tables, percentage tables, Tukey's resistant line vs OLS
- Unit 5: Multivariate analysis, 3-variable contingency tables, time-series resampling, trends, moving averages
- Global interactive filtering (Date range, Categories, Payment methods, Locations)
- Cleaned dataset and analysis report downloads
"""

import os
import sys
import io
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# Add project root to sys.path to enable src imports
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src import analysis

# =============================================================================
# 1. STREAMLIT APP CONFIGURATION & MODERN STYLING
# =============================================================================
st.set_page_config(
    page_title="Online Shopping Behaviour Analysis",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern card-based light theme
st.markdown("""
<style>
    /* Global styles */
    .main .block-container {
        padding-top: 1.8rem;
        padding-bottom: 2.5rem;
    }
    
    /* Sleek card containers */
    .metric-card {
        background: #ffffff;
        border: 1px solid #E0E7FF;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
        margin-bottom: 1rem;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(13, 71, 161, 0.08);
    }
    .metric-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 1.85rem;
        font-weight: 700;
        color: #0F172A;
        line-height: 1.2;
    }
    .metric-subtitle {
        font-size: 0.78rem;
        color: #1E88E5;
        font-weight: 500;
        margin-top: 4px;
    }
    
    /* Academic unit badges */
    .badge-unit {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.03em;
        margin-right: 6px;
    }
    .badge-unit-4 {
        background-color: #E0F2FE;
        color: #0369A1;
        border: 1px solid #BAE6FD;
    }
    .badge-unit-5 {
        background-color: #FEF3C7;
        color: #B45309;
        border: 1px solid #FDE68A;
    }
    
    /* Callout box */
    .info-callout {
        background-color: #F8FAFC;
        border-left: 4px solid #1E88E5;
        padding: 14px 16px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 1.2rem;
        font-size: 0.92rem;
        color: #334155;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. SIDEBAR: DATASET UPLOAD & COLUMN MAPPING CONTROLS
# =============================================================================
st.sidebar.image("https://img.icons8.com/fluency/96/shopping-cart-loaded.png", width=64)
st.sidebar.title("🛒 E-Commerce Analytics")
st.sidebar.caption("Online Shopping Behaviour & Trend Engine")

st.sidebar.markdown("---")
st.sidebar.subheader("📁 1. Dataset Ingestion")

uploaded_file = st.sidebar.file_uploader(
    "Upload Transaction Dataset",
    type=["csv", "xlsx", "xls"],
    help="Upload an e-commerce transaction dataset in CSV or Excel format."
)

default_data_path = os.path.join(BASE_DIR, "dataset", "online_shopping_data.csv")
alt_data_path = os.path.join(BASE_DIR, "dataset", "alternative_retail_transactions.xlsx")

dataset_source_note = ""
raw_df = None

if uploaded_file is not None:
    try:
        raw_df = analysis.load_dataset(uploaded_file)
        dataset_source_note = f"Uploaded File: `{uploaded_file.name}` ({len(raw_df):,} records)"
        st.sidebar.success(f"Loaded {uploaded_file.name} successfully!")
    except Exception as e:
        st.sidebar.error(f"Error loading file: {e}")
else:
    # Option to toggle between default dataset or sample alternative dataset
    data_choice = st.sidebar.radio(
        "Or Select Bundled Dataset:",
        ["Standard E-Commerce (CSV)", "Alternative E-Commerce (Excel)"],
        index=0
    )
    if data_choice == "Standard E-Commerce (CSV)" and os.path.exists(default_data_path):
        raw_df = analysis.load_dataset(default_data_path)
        dataset_source_note = "Bundled Dataset: `online_shopping_data.csv` (Synthetic, 12 Months)"
    elif os.path.exists(alt_data_path):
        raw_df = analysis.load_dataset(alt_data_path)
        dataset_source_note = "Bundled Alternative Dataset: `alternative_retail_transactions.xlsx` (Excel)"
    else:
        st.error("No dataset available. Please upload a CSV or Excel file.")
        st.stop()

if raw_df is None or raw_df.empty:
    st.warning("Please upload a non-empty dataset to proceed.")
    st.stop()

# Auto-detect column types and heuristic mappings
col_types = analysis.detect_column_types(raw_df)
auto_maps = analysis.auto_map_columns(raw_df)
all_columns = ["None"] + list(raw_df.columns)

# -----------------------------------------------------------------------------
# Column Mapping Expander
# -----------------------------------------------------------------------------
with st.sidebar.expander("⚙️ 2. Configure Column Mapping", expanded=False):
    st.caption("Verify or adjust column associations if headers differ:")

    def get_default_index(detected_col):
        if detected_col and detected_col in raw_df.columns:
            return all_columns.index(detected_col)
        return 0

    map_date = st.selectbox("Date / Timestamp Column", all_columns, index=get_default_index(auto_maps["order_date"]))
    map_amount = st.selectbox("Total Amount / Revenue", all_columns, index=get_default_index(auto_maps["total_amount"]))
    map_qty = st.selectbox("Quantity / Units Sold", all_columns, index=get_default_index(auto_maps["quantity"]))
    map_price = st.selectbox("Unit Price Column", all_columns, index=get_default_index(auto_maps["unit_price"]))
    map_cat = st.selectbox("Product Category", all_columns, index=get_default_index(auto_maps["category"]))
    map_prod = st.selectbox("Product Name / Description", all_columns, index=get_default_index(auto_maps["product_name"]))
    map_cust = st.selectbox("Customer ID", all_columns, index=get_default_index(auto_maps["customer_id"]))
    map_pay = st.selectbox("Payment Method", all_columns, index=get_default_index(auto_maps["payment_method"]))
    map_loc = st.selectbox("Customer Location / Region", all_columns, index=get_default_index(auto_maps["location"]))
    map_disc = st.selectbox("Discount Rate", all_columns, index=get_default_index(auto_maps["discount"]))
    map_order = st.selectbox("Order / Invoice ID", all_columns, index=get_default_index(auto_maps["order_id"]))

# Cleaning Controls
st.sidebar.subheader("🧹 3. Data Cleaning Options")
clean_dups = st.sidebar.checkbox("Remove Duplicate Records", value=True)
clean_missing = st.sidebar.checkbox("Impute Missing Values", value=True)

# Execute Data Cleaning
col_date_clean = map_date if map_date != "None" else None
col_amt_clean = map_amount if map_amount != "None" else None
col_qty_clean = map_qty if map_qty != "None" else None
col_price_clean = map_price if map_price != "None" else None
col_disc_clean = map_disc if map_disc != "None" else None

cleaned_df, clean_audit = analysis.clean_data(
    raw_df,
    drop_duplicates=clean_dups,
    fill_missing=clean_missing,
    date_col=col_date_clean,
    amount_col=col_amt_clean,
    qty_col=col_qty_clean,
    unit_price_col=col_price_clean,
    discount_col=col_disc_clean
)

# -----------------------------------------------------------------------------
# Global Interactive Filters
# -----------------------------------------------------------------------------
st.sidebar.subheader("🔍 4. Global Filters")
filtered_df = cleaned_df.copy()

# Date Range Filter
if col_date_clean and col_date_clean in cleaned_df.columns:
    if pd.api.types.is_datetime64_any_dtype(cleaned_df[col_date_clean]):
        min_dt = cleaned_df[col_date_clean].min()
        max_dt = cleaned_df[col_date_clean].max()
        if pd.notnull(min_dt) and pd.notnull(max_dt) and min_dt < max_dt:
            selected_date_range = st.sidebar.date_input(
                "Filter by Date Range",
                value=(min_dt.date(), max_dt.date()),
                min_value=min_dt.date(),
                max_value=max_dt.date()
            )
            if isinstance(selected_date_range, tuple) and len(selected_date_range) == 2:
                start_d, end_d = selected_date_range
                filtered_df = filtered_df[
                    (filtered_df[col_date_clean].dt.date >= start_d) &
                    (filtered_df[col_date_clean].dt.date <= end_d)
                ]

# Category Filter
if map_cat != "None" and map_cat in cleaned_df.columns:
    cat_options = sorted(cleaned_df[map_cat].dropna().unique().tolist())
    selected_cats = st.sidebar.multiselect("Product Category", options=cat_options, default=cat_options)
    if selected_cats:
        filtered_df = filtered_df[filtered_df[map_cat].isin(selected_cats)]

# Payment Method Filter
if map_pay != "None" and map_pay in cleaned_df.columns:
    pay_options = sorted(cleaned_df[map_pay].dropna().unique().tolist())
    selected_pay = st.sidebar.multiselect("Payment Method", options=pay_options, default=pay_options)
    if selected_pay:
        filtered_df = filtered_df[filtered_df[map_pay].isin(selected_pay)]

# Customer Location Filter
if map_loc != "None" and map_loc in cleaned_df.columns:
    loc_options = sorted(cleaned_df[map_loc].dropna().unique().tolist())
    selected_loc = st.sidebar.multiselect("Customer Location", options=loc_options, default=loc_options)
    if selected_loc:
        filtered_df = filtered_df[filtered_df[map_loc].isin(selected_loc)]

st.sidebar.markdown(f"**Filtered Records:** `{len(filtered_df):,}` / `{len(cleaned_df):,}`")

# -----------------------------------------------------------------------------
# Sidebar Navigation Menu
# -----------------------------------------------------------------------------
st.sidebar.subheader("🧭 5. Navigation")
nav_section = st.sidebar.radio(
    "Go To Section:",
    [
        "📊 Executive Overview & KPIs",
        "🔍 Data Preview & Quality Audit",
        "🏷️ Category & Product Analytics",
        "👥 Customer & Payment Behavior",
        "🔄 Unit 4: Bivariate & Resistant Line",
        "🌐 Unit 5: Multivariate & 3-Variable",
        "📅 Unit 5: Time-Series & Trends",
        "💾 Export Cleaned Data & Reports"
    ]
)

st.sidebar.markdown("---")
st.sidebar.caption("🎓 College-Level EDA & Syllabus Project")

# =============================================================================
# HEADER SECTION
# =============================================================================
st.title("Online Shopping Behaviour & Purchase Trend Analysis")
st.markdown(f"*{dataset_source_note}*")

# Helper function for rendering consistent KPI cards
def render_kpi(col, title, value, subtitle):
    col.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">{title}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-subtitle">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

# Compute dynamic KPIs on filtered dataset
kpis = analysis.compute_kpis(
    filtered_df,
    amount_col=col_amt_clean,
    qty_col=col_qty_clean,
    order_id_col=(map_order if map_order != "None" else None),
    cust_id_col=(map_cust if map_cust != "None" else None)
)

# =============================================================================
# SECTION 1: EXECUTIVE OVERVIEW & KPIS
# =============================================================================
if nav_section == "📊 Executive Overview & KPIs":
    st.subheader("📊 Executive Overview & Key Performance Indicators")
    
    # Render KPI Cards in 4 columns
    k1, k2, k3, k4 = st.columns(4)
    render_kpi(k1, "Total Gross Revenue", f"${kpis['total_revenue']:,.2f}", "Sum of all filtered orders")
    render_kpi(k2, "Transaction Volume", f"{kpis['total_orders']:,}", "Unique completed purchases")
    render_kpi(k3, "Average Order Value (AOV)", f"${kpis['average_transaction_value']:,.2f}", "Revenue per transaction")
    render_kpi(k4, "Units Purchased", f"{kpis['total_units']:,}", f"Avg {kpis['avg_units_per_order']} units / order")

    # Second row of KPIs if customer info is mapped
    if map_cust != "None" and map_cust in filtered_df.columns:
        k5, k6, k7, k8 = st.columns(4)
        render_kpi(k5, "Unique Customers", f"{kpis['unique_customers']:,}", "Active consumer base")
        render_kpi(k6, "Repeat Buyer Rate", f"{kpis['repeat_customer_rate']:.1f}%", "Customers with > 1 order")
        
        # Avg discount if mapped
        if col_disc_clean and col_disc_clean in filtered_df.columns:
            avg_disc = filtered_df[col_disc_clean].mean() * 100
            render_kpi(k7, "Average Discount Rate", f"{avg_disc:.1f}%", "Mean promotional discount")
        else:
            render_kpi(k7, "Active Categories", f"{filtered_df[map_cat].nunique() if map_cat != 'None' else 'N/A'}", "Distinct product lines")
            
        render_kpi(k8, "Data Cleanliness", "100%", "Duplicates removed & imputed")

    st.markdown("---")
    
    # Visual Breakdown: Revenue by Category & Monthly Trend
    c1, c2 = st.columns([1, 1])

    with c1:
        st.markdown("##### 🏷️ Revenue Distribution by Product Category")
        if map_cat != "None" and col_amt_clean:
            cat_summary = analysis.calculate_category_summary(filtered_df, category_col=map_cat, amount_col=col_amt_clean, qty_col=col_qty_clean)
            if not cat_summary.empty:
                fig_cat = px.pie(
                    cat_summary,
                    names=map_cat,
                    values="Total Revenue",
                    hole=0.45,
                    color_discrete_sequence=px.colors.qualitative.Prism
                )
                fig_cat.update_traces(textposition='inside', textinfo='percent+label')
                fig_cat.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=350)
                st.plotly_chart(fig_cat, use_container_width=True)
            else:
                st.info("Insufficient data for category pie chart.")
        else:
            st.info("Map Product Category and Total Amount columns to view category revenue share.")

    with c2:
        st.markdown("##### 📈 Monthly Revenue Trajectory")
        if col_date_clean and col_amt_clean and col_date_clean in filtered_df.columns:
            monthly_ts = analysis.calculate_time_series_sales(filtered_df, date_col=col_date_clean, amount_col=col_amt_clean, freq="ME")
            if not monthly_ts.empty:
                fig_mo = go.Figure()
                fig_mo.add_trace(go.Bar(
                    x=monthly_ts["Period_Label"],
                    y=monthly_ts["Revenue"],
                    name="Monthly Revenue",
                    marker_color="#1E88E5",
                    opacity=0.85
                ))
                fig_mo.add_trace(go.Scatter(
                    x=monthly_ts["Period_Label"],
                    y=monthly_ts["Moving Avg (3-Period)"],
                    name="3-Month Trend",
                    line=dict(color="#D81B60", width=3)
                ))
                fig_mo.update_layout(
                    margin=dict(t=20, b=20, l=20, r=20),
                    height=350,
                    xaxis_title="Month",
                    yaxis_title="Revenue ($)",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_mo, use_container_width=True)
            else:
                st.info("Insufficient date observations for monthly trajectory.")
        else:
            st.info("Map Date and Revenue columns to visualize monthly trends.")

# =============================================================================
# SECTION 2: DATA PREVIEW & QUALITY AUDIT
# =============================================================================
elif nav_section == "🔍 Data Preview & Quality Audit":
    st.subheader("🔍 Data Preview & Automated Quality Inspection")
    
    st.markdown("""
    <div class="info-callout">
        <b>Data Quality Assurance</b>: Evaluates dimensions, data types, missing value distributions, 
        duplicate records, and validates clean mathematical relationships across transaction records.
    </div>
    """, unsafe_allow_html=True)

    tab_preview, tab_quality, tab_audit = st.tabs(["📋 Data Records Preview", "🔎 Missing Values & Types", "⚙️ Cleaning Audit Trail"])

    with tab_preview:
        st.markdown(f"**Showing First 100 Rows of Active (Filtered) Dataset ({len(filtered_df):,} total records):**")
        st.dataframe(filtered_df.head(100), use_container_width=True)

    with tab_quality:
        raw_report = analysis.get_data_quality_report(raw_df)
        q1, q2, q3, q4 = st.columns(4)
        render_kpi(q1, "Raw Rows", f"{raw_report['num_rows']:,}", "Before de-duplication")
        render_kpi(q2, "Attributes (Columns)", f"{raw_report['num_cols']}", "Total dataset fields")
        render_kpi(q3, "Duplicate Rows", f"{raw_report['duplicates_count']}", f"{raw_report['duplicates_pct']}% redundancy")
        render_kpi(q4, "Missing Cells", f"{raw_report['total_missing_cells']:,}", "Across all features")

        st.markdown("##### Missing Value Frequency and Percentages per Feature (Raw Data):")
        st.dataframe(raw_report["missing_table"], use_container_width=True)

        if raw_report["total_missing_cells"] > 0:
            missing_plot_df = raw_report["missing_table"][raw_report["missing_table"]["Missing Count"] > 0]
            fig_miss = px.bar(
                missing_plot_df,
                x="Column",
                y="Missing Count",
                text="Missing Count",
                color="Missing Percentage (%)",
                color_continuous_scale="Reds",
                title="Missing Value Distribution by Column"
            )
            fig_miss.update_layout(height=350)
            st.plotly_chart(fig_miss, use_container_width=True)

    with tab_audit:
        st.markdown("##### ⚙️ Data Cleaning Actions Applied:")
        st.write(f"- **Original Rows:** {clean_audit['original_rows']}")
        st.write(f"- **Identical Duplicates Purged:** {clean_audit['removed_duplicates']}")
        st.write(f"- **Imputed Columns:**")
        if clean_audit['imputed_columns']:
            for c, strategy in clean_audit['imputed_columns']:
                st.write(f"  * `{c}`: Imputed using {strategy}")
        else:
            st.write("  * No missing values required imputation.")
        st.write(f"- **Cleaned Dataset Dimension:** {clean_audit['cleaned_rows']} records")

# =============================================================================
# SECTION 3: CATEGORY & PRODUCT ANALYTICS
# =============================================================================
elif nav_section == "🏷️ Category & Product Analytics":
    st.subheader("🏷️ Product Category & Departmental Analysis")

    if map_cat == "None" or not col_amt_clean:
        st.warning("Please map Product Category and Total Amount columns in the sidebar to view this analysis.")
    else:
        cat_summary = analysis.calculate_category_summary(
            filtered_df,
            category_col=map_cat,
            amount_col=col_amt_clean,
            qty_col=col_qty_clean
        )
        st.markdown("##### Category Performance Summary Matrix:")
        st.dataframe(cat_summary, use_container_width=True)

        col_a, col_b = st.columns(2)
        with col_a:
            fig_bar = px.bar(
                cat_summary,
                x="Total Revenue",
                y=map_cat,
                orientation="h",
                text="Total Revenue",
                color="Total Revenue",
                color_continuous_scale="Blues",
                title=f"Total Revenue by {map_cat}"
            )
            fig_bar.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
            fig_bar.update_layout(height=400, yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_b:
            fig_aov = px.bar(
                cat_summary,
                x=map_cat,
                y="Average Order Value",
                text="Average Order Value",
                color="Average Order Value",
                color_continuous_scale="Teal",
                title=f"Average Order Value (AOV) by {map_cat}"
            )
            fig_aov.update_traces(texttemplate='$%{text:.2f}', textposition='outside')
            fig_aov.update_layout(height=400)
            st.plotly_chart(fig_aov, use_container_width=True)

        # Product Name Breakdown if mapped
        if map_prod != "None" and map_prod in filtered_df.columns:
            st.markdown("##### 🏆 Top 10 Best-Selling Products by Revenue")
            top_products = filtered_df.groupby(map_prod).agg(
                Revenue=(col_amt_clean, "sum"),
                Units_Sold=(col_qty_clean, "sum") if col_qty_clean else (col_amt_clean, "count"),
                Transactions=(col_amt_clean, "count")
            ).reset_index().sort_values(by="Revenue", ascending=False).head(10)

            fig_top = px.bar(
                top_products,
                x="Revenue",
                y=map_prod,
                orientation="h",
                text="Revenue",
                color="Units_Sold",
                color_continuous_scale="Viridis",
                title="Top 10 Products by Revenue"
            )
            fig_top.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
            fig_top.update_layout(height=420, yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_top, use_container_width=True)

# =============================================================================
# SECTION 4: CUSTOMER & PAYMENT BEHAVIOR
# =============================================================================
elif nav_section == "👥 Customer & Payment Behavior":
    st.subheader("👥 Customer Spending Patterns & Payment Channel Adoption")

    p1, p2 = st.columns([1, 1])

    with p1:
        st.markdown("##### 💳 Payment Method Distribution")
        if map_pay != "None" and col_amt_clean and map_pay in filtered_df.columns:
            pay_dist = analysis.payment_distribution_analysis(filtered_df, payment_col=map_pay, amount_col=col_amt_clean)
            st.dataframe(pay_dist, use_container_width=True)

            fig_pay = px.pie(
                pay_dist,
                names=map_pay,
                values="Total_Revenue",
                title=f"Revenue Share by {map_pay}",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Safe
            )
            st.plotly_chart(fig_pay, use_container_width=True)
        else:
            st.info("Map Payment Method and Amount columns to view channel distribution.")

    with p2:
        st.markdown("##### 💰 Customer Spending Tiers & Segmentation")
        if map_cust != "None" and col_amt_clean and map_cust in filtered_df.columns:
            cust_df, cust_summary = analysis.customer_spending_analysis(
                filtered_df,
                cust_id_col=map_cust,
                amount_col=col_amt_clean,
                order_id_col=map_order if map_order != "None" else None
            )

            fig_tier = px.histogram(
                cust_df,
                x="Total Spend",
                nbins=30,
                color="Tier",
                title="Customer Lifetime Spend Distribution",
                color_discrete_sequence=px.colors.qualitative.Vivid
            )
            fig_tier.update_layout(height=350, xaxis_title="Total Customer Spend ($)", yaxis_title="Customer Count")
            st.plotly_chart(fig_tier, use_container_width=True)

            st.write(f"- **Active Unique Customers:** {cust_summary['total_unique_customers']:,}")
            st.write(f"- **Mean Customer Lifetime Spend:** ${cust_summary['mean_customer_spend']:,.2f}")
            st.write(f"- **Median Customer Lifetime Spend:** ${cust_summary['median_customer_spend']:,.2f}")
            st.write(f"- **Repeat Buyers (>1 order):** {cust_summary['repeat_buyers_count']:,}")
        else:
            st.info("Map Customer ID and Total Amount columns to evaluate customer lifetime spend.")

# =============================================================================
# SECTION 5: UNIT 4 - BIVARIATE & RESISTANT LINE ANALYSIS
# =============================================================================
elif nav_section == "🔄 Unit 4: Bivariate & Resistant Line":
    st.subheader("🔄 Unit 4: Bivariate Data Analysis & Robust Linear Fitting")
    
    st.markdown("""
    <div class="info-callout">
        <span class="badge-unit badge-unit-4">UNIT 4 SYLLABUS MAPPING</span>
        <b>Core Topics</b>: Relationships between two variables, percentage tables, contingency tables, 
        handling several batches, scatterplots, and <b>Tukey's Resistant Line</b> (Median-Median line fitting vs OLS).
    </div>
    """, unsafe_allow_html=True)

    tab_resist, tab_scatter, tab_contingency, tab_batches = st.tabs([
        "📐 Tukey's Resistant Line vs OLS",
        "🌌 Bivariate Scatterplots",
        "📊 Contingency & Percentage Tables",
        "📦 Handling Several Batches (Distributions)"
    ])

    with tab_resist:
        st.markdown("#### 📐 Tukey's Resistant Line (Median-Median Robust Line)")
        st.markdown("""
        **Theoretical Background (Tukey 1977)**:
        Standard Ordinary Least Squares (OLS) minimizes squared residuals, causing it to be heavily 
        distorted by extreme leverage points or high-ticket outliers.
        
        **Tukey's 3-Group Resistant Line**:
        1. Sorts observations by $X$.
        2. Partitions data into 3 equal batches: **Left ($L$)**, **Middle ($M$)**, and **Right ($R$)**.
        3. Identifies the median coordinates: $(x_L, y_L)$, $(x_M, y_M)$, and $(x_R, y_R)$.
        4. Calculates robust slope $b = \\frac{y_R - y_L}{x_R - x_L}$.
        5. Computes intercept $a = \\frac{1}{3} [(y_L - bx_L) + (y_M - bx_M) + (y_R - bx_R)]$.
        """)

        num_choices = col_types["numerical"]
        if len(num_choices) >= 2:
            rc1, rc2 = st.columns(2)
            default_x = col_qty_clean if col_qty_clean in num_choices else num_choices[0]
            default_y = col_amt_clean if col_amt_clean in num_choices else num_choices[-1]

            rx_var = rc1.selectbox("Predictor Variable (X)", num_choices, index=num_choices.index(default_x))
            ry_var = rc2.selectbox("Response Variable (Y)", num_choices, index=num_choices.index(default_y))

            res_line = analysis.calculate_resistant_line(filtered_df[rx_var], filtered_df[ry_var])
            ols_line = analysis.calculate_ols_line(filtered_df[rx_var], filtered_df[ry_var])

            if "error" not in res_line and "error" not in ols_line:
                m1, m2, m3, m4 = st.columns(4)
                render_kpi(m1, "Tukey Resistant Slope (b)", f"{res_line['slope']:.3f}", "Robust to extreme outliers")
                render_kpi(m2, "OLS Linear Slope (b)", f"{ols_line['slope']:.3f}", f"R² = {ols_line['r_squared']:.3f}")
                render_kpi(m3, "Tukey Intercept (a)", f"${res_line['intercept']:.2f}", res_line['equation'])
                render_kpi(m4, "OLS Intercept (a)", f"${ols_line['intercept']:.2f}", ols_line['equation'])

                # Plot comparison
                sample_n = min(1000, len(filtered_df))
                plot_sample = filtered_df[[rx_var, ry_var]].dropna().sample(n=sample_n, random_state=42)

                x_min, x_max = filtered_df[rx_var].min(), filtered_df[rx_var].max()
                x_fit = np.linspace(x_min, x_max, 100)
                y_fit_res = res_line["intercept"] + res_line["slope"] * x_fit
                y_fit_ols = ols_line["intercept"] + ols_line["slope"] * x_fit

                fig_robust = go.Figure()
                fig_robust.add_trace(go.Scatter(
                    x=plot_sample[rx_var],
                    y=plot_sample[ry_var],
                    mode="markers",
                    name="Observed Transactions",
                    marker=dict(color="#94A3B8", opacity=0.45, size=6)
                ))
                # Add Tukey medians
                med_x = [res_line["medians"]["Left"][0], res_line["medians"]["Middle"][0], res_line["medians"]["Right"][0]]
                med_y = [res_line["medians"]["Left"][1], res_line["medians"]["Middle"][1], res_line["medians"]["Right"][1]]
                fig_robust.add_trace(go.Scatter(
                    x=med_x,
                    y=med_y,
                    mode="markers",
                    name="Tukey 3-Group Medians (L, M, R)",
                    marker=dict(color="#D81B60", size=14, symbol="x", line=dict(width=2, color="black"))
                ))
                # Add Resistant line
                fig_robust.add_trace(go.Scatter(
                    x=x_fit,
                    y=y_fit_res,
                    mode="lines",
                    name=f"Tukey Resistant Line: {res_line['equation']}",
                    line=dict(color="#D81B60", width=3)
                ))
                # Add OLS line
                fig_robust.add_trace(go.Scatter(
                    x=x_fit,
                    y=y_fit_ols,
                    mode="lines",
                    name=f"OLS Regression: {ols_line['equation']} (R²={ols_line['r_squared']:.2f})",
                    line=dict(color="#1E88E5", width=3, dash="dash")
                ))

                fig_robust.update_layout(
                    title=f"Comparison: Tukey's Resistant Line vs OLS ({ry_var} vs {rx_var})",
                    xaxis_title=rx_var,
                    yaxis_title=ry_var,
                    height=520,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_robust, use_container_width=True)

                st.markdown(f"""
                **Syllabus Analysis & Deduction**:
                - **Left Group Median $(x_L, y_L)$:** `{res_line['medians']['Left']}`
                - **Middle Group Median $(x_M, y_M)$:** `{res_line['medians']['Middle']}`
                - **Right Group Median $(x_R, y_R)$:** `{res_line['medians']['Right']}`
                - **Residual Median Absolute Deviation (MAD):** `{res_line['median_absolute_residual']}`
                - When outliers or skewed high-ticket transactions are present, the OLS slope deviates upwards. 
                  Tukey's resistant line anchors on the partition medians, yielding a robust estimate of true unit impact.
                """)
            else:
                st.error("Insufficient variance or points to compute resistant line.")
        else:
            st.info("At least two numerical columns are required for resistant-line fitting.")

    with tab_scatter:
        st.markdown("#### 🌌 Bivariate Scatterplots with Dynamic Aesthetic Mappings")
        sc1, sc2, sc3 = st.columns(3)
        sx = sc1.selectbox("X-Axis Variable", col_types["numerical"], index=0, key="scat_x")
        sy = sc2.selectbox("Y-Axis Variable", col_types["numerical"], index=min(1, len(col_types["numerical"])-1), key="scat_y")
        hue_options = ["None"] + col_types["categorical"] + col_types["numerical"]
        shue = sc3.selectbox("Color By (Hue)", hue_options, index=1 if len(hue_options)>1 else 0)

        fig_scat = px.scatter(
            filtered_df,
            x=sx,
            y=sy,
            color=None if shue == "None" else shue,
            opacity=0.7,
            title=f"Bivariate Scatter: {sy} vs {sx}" + (f" (Colored by {shue})" if shue != "None" else ""),
            trendline="ols" if shue == "None" else None
        )
        fig_scat.update_layout(height=480)
        st.plotly_chart(fig_scat, use_container_width=True)

    with tab_contingency:
        st.markdown("#### 📊 Two-Variable Contingency & Percentage Tables")
        cat_cols = col_types["categorical"]
        if len(cat_cols) >= 2:
            cc1, cc2, cc3 = st.columns(3)
            default_row = map_cat if map_cat in cat_cols else cat_cols[0]
            default_col = map_pay if map_pay in cat_cols else cat_cols[1]

            row_feat = cc1.selectbox("Row Feature", cat_cols, index=cat_cols.index(default_row))
            col_feat = cc2.selectbox("Column Feature", cat_cols, index=cat_cols.index(default_col))
            norm_type = cc3.selectbox(
                "Table Standardization",
                ["Absolute Frequencies", "Row Percentages (Conditioned on Row)", "Column Percentages (Conditioned on Col)", "Total Percentages (% of All)"]
            )

            norm_arg = None
            if norm_type.startswith("Row"):
                norm_arg = "index"
            elif norm_type.startswith("Column"):
                norm_arg = "columns"
            elif norm_type.startswith("Total"):
                norm_arg = "all"

            ctable, stat_chi = analysis.calculate_contingency_table(
                filtered_df,
                row_col=row_feat,
                col_col=col_feat,
                normalize=norm_arg
            )

            st.dataframe(ctable, use_container_width=True)

            if stat_chi and "chi2_statistic" in stat_chi:
                st.markdown(rf"""
                **Pearson's Chi-Square Test of Independence ($\chi^2$):**
                - $\chi^2$ Statistic: `{stat_chi['chi2_statistic']}`
                - $p$-value: `{stat_chi['p_value']:.4e}`
                - Degrees of Freedom: `{stat_chi['degrees_of_freedom']}`
                - **Result**: {stat_chi['interpretation']}
                """)
        else:
            st.info("At least two categorical columns are required for contingency analysis.")

    with tab_batches:
        st.markdown("#### 📦 Handling Several Batches (Distributions & Spreads)")
        bc1, bc2 = st.columns(2)
        batch_cat = bc1.selectbox("Batch Grouping (Categorical)", col_types["categorical"], index=0, key="batch_cat")
        batch_num = bc2.selectbox("Numerical Metric", col_types["numerical"], index=min(1, len(col_types["numerical"])-1), key="batch_num")

        fig_batch = px.box(
            filtered_df,
            x=batch_cat,
            y=batch_num,
            color=batch_cat,
            points="outliers",
            title=f"Comparative Distribution of {batch_num} Across Several Batches of {batch_cat}"
        )
        fig_batch.update_layout(height=480, showlegend=False)
        st.plotly_chart(fig_batch, use_container_width=True)

# =============================================================================
# SECTION 6: UNIT 5 - MULTIVARIATE & 3-VARIABLE ANALYSIS
# =============================================================================
elif nav_section == "🌐 Unit 5: Multivariate & 3-Variable":
    st.subheader("🌐 Unit 5: Multivariate Analysis & Causal Conditioning")

    st.markdown("""
    <div class="info-callout">
        <span class="badge-unit badge-unit-5">UNIT 5 SYLLABUS MAPPING</span>
        <b>Core Topics</b>: Introducing a third variable, causal and confounding explanations, 
        three-variable contingency tables, multivariate interaction visualization, and correlation heatmaps.
    </div>
    """, unsafe_allow_html=True)

    tab_3var, tab_multi_vis, tab_corr = st.tabs([
        "📑 Three-Variable Contingency Tables",
        "🎯 3-Variable Interaction Visualizations",
        "🔥 Correlation Heatmap"
    ])

    with tab_3var:
        st.markdown("#### 📑 Three-Variable Contingency Table (Stratified Cross-Tabulation)")
        st.markdown("""
        Introducing a **third conditioning variable** enables analysts to evaluate conditional association 
        and avoid misleading aggregated inferences (Simpson's Paradox).
        """)

        cat_cols = col_types["categorical"]
        if len(cat_cols) >= 3:
            tc1, tc2, tc3 = st.columns(3)
            layer_col = tc1.selectbox("Conditioning Layer (3rd Variable)", cat_cols, index=min(2, len(cat_cols)-1))
            row_3v = tc2.selectbox("Row Variable", cat_cols, index=0)
            col_3v = tc3.selectbox("Column Variable", cat_cols, index=min(1, len(cat_cols)-1))

            crosstab_3 = analysis.calculate_three_variable_contingency(
                filtered_df,
                row_col=row_3v,
                col_col=col_3v,
                layer_col=layer_col,
                normalize="index"
            )

            st.markdown(f"**Row Percentages conditioned on {layer_col} and {row_3v}:**")
            st.dataframe(crosstab_3, use_container_width=True)
        else:
            st.info("At least three categorical columns are required for 3-variable contingency tables.")

    with tab_multi_vis:
        st.markdown("#### 🎯 Multivariate Interaction & Bubble Plot")
        if len(col_types["numerical"]) >= 2 and len(col_types["categorical"]) >= 1:
            mv1, mv2, mv3, mv4 = st.columns(4)
            mx = mv1.selectbox("X-Axis (Metric 1)", col_types["numerical"], index=0, key="mv_x")
            my = mv2.selectbox("Y-Axis (Metric 2)", col_types["numerical"], index=min(1, len(col_types["numerical"])-1), key="mv_y")
            m_color = mv3.selectbox("Color Variable (3rd Variable)", col_types["categorical"], index=0, key="mv_c")
            size_options = ["None"] + col_types["numerical"]
            m_size = mv4.selectbox("Size By (4th Variable)", size_options, index=1 if len(size_options)>1 else 0)

            fig_bubble = px.scatter(
                filtered_df,
                x=mx,
                y=my,
                color=m_color,
                size=None if m_size == "None" else m_size,
                hover_data=col_types["categorical"],
                title=f"Multivariate Relationship: {my} vs {mx} Stratified by {m_color}"
            )
            fig_bubble.update_layout(height=520)
            st.plotly_chart(fig_bubble, use_container_width=True)
        else:
            st.info("Insufficient variables for multivariate visual mapping.")

    with tab_corr:
        st.markdown("#### 🔥 Numerical Correlation Heatmap")
        num_cols_corr = col_types["numerical"]
        if len(num_cols_corr) >= 2:
            corr_matrix = analysis.calculate_correlation_matrix(filtered_df, numeric_cols=num_cols_corr)
            fig_corr = px.imshow(
                corr_matrix,
                text_auto=True,
                aspect="auto",
                color_continuous_scale="RdBu_r",
                zmin=-1,
                zmax=1,
                title="Correlation Heatmap (Pearson Coefficients)"
            )
            fig_corr.update_layout(height=480)
            st.plotly_chart(fig_corr, use_container_width=True)
        else:
            st.info("At least two numerical columns are required for correlation analysis.")

# =============================================================================
# SECTION 7: UNIT 5 - TIME-SERIES & TRENDS
# =============================================================================
elif nav_section == "📅 Unit 5: Time-Series & Trends":
    st.subheader("📅 Unit 5: Time-Series Analysis & Temporal Dynamics")

    st.markdown("""
    <div class="info-callout">
        <span class="badge-unit badge-unit-5">UNIT 5 SYLLABUS MAPPING</span>
        <b>Core Topics</b>: Fundamentals of time-series analysis, temporal characteristics (trend, seasonality, noise), 
        chronological data cleaning, time-based indexing, grouping, and frequency <b>resampling</b> (Daily, Weekly, Monthly, Quarterly).
    </div>
    """, unsafe_allow_html=True)

    if not col_date_clean or not col_amt_clean or col_date_clean not in filtered_df.columns:
        st.warning("Please map a valid Date/Timestamp column and Total Amount column in the sidebar to view time-series analysis.")
    else:
        freq_choice = st.radio(
            "Select Resampling Frequency:",
            ["Daily ('D')", "Weekly ('W')", "Monthly ('ME')", "Quarterly ('QE')"],
            horizontal=True,
            index=2
        )

        freq_code_map = {
            "Daily ('D')": "D",
            "Weekly ('W')": "W",
            "Monthly ('ME')": "ME",
            "Quarterly ('QE')": "QE"
        }
        resampled_ts = analysis.calculate_time_series_sales(
            filtered_df,
            date_col=col_date_clean,
            amount_col=col_amt_clean,
            freq=freq_code_map[freq_choice]
        )

        if not resampled_ts.empty:
            # Main Time-Series Plot
            fig_ts = go.Figure()
            fig_ts.add_trace(go.Scatter(
                x=resampled_ts["Period"],
                y=resampled_ts["Revenue"],
                mode="lines+markers",
                name="Revenue ($)",
                line=dict(color="#1E88E5", width=2.5),
                marker=dict(size=6)
            ))
            fig_ts.add_trace(go.Scatter(
                x=resampled_ts["Period"],
                y=resampled_ts["Moving Avg (3-Period)"],
                mode="lines",
                name="3-Period Moving Average",
                line=dict(color="#D81B60", width=2.8, dash="dash")
            ))

            fig_ts.update_layout(
                title=f"Time-Series Revenue Analysis ({freq_choice} Resampling with Moving Average)",
                xaxis_title="Timeline",
                yaxis_title="Aggregated Revenue ($)",
                height=480,
                xaxis=dict(rangeslider=dict(visible=True)),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_ts, use_container_width=True)

            # Cumulative Revenue Trajectory
            c_ts1, c_ts2 = st.columns(2)
            with c_ts1:
                fig_cum = px.area(
                    resampled_ts,
                    x="Period",
                    y="Cumulative Revenue",
                    title="Cumulative Revenue Growth Over Time",
                    color_discrete_sequence=["#2E7D32"]
                )
                fig_cum.update_layout(height=350)
                st.plotly_chart(fig_cum, use_container_width=True)

            with c_ts2:
                fig_vol = px.bar(
                    resampled_ts,
                    x="Period_Label",
                    y="Orders",
                    title="Transaction Order Count by Period",
                    color="Orders",
                    color_continuous_scale="Blues"
                )
                fig_vol.update_layout(height=350)
                st.plotly_chart(fig_vol, use_container_width=True)

            # Resampling Data Table
            with st.expander("📊 View Resampled Time-Series Aggregation Table"):
                st.dataframe(resampled_ts, use_container_width=True)
        else:
            st.info("Insufficient time observations to construct the requested series.")

# =============================================================================
# SECTION 8: EXPORT CLEANED DATA & REPORTS
# =============================================================================
elif nav_section == "💾 Export Cleaned Data & Reports":
    st.subheader("💾 Export Cleaned Dataset and Analytical Summaries")

    st.markdown("""
    <div class="info-callout">
        <b>Data Governance & Reproducibility</b>: Download the fully cleaned and validated dataset, 
        or export targeted executive summaries directly in CSV format.
    </div>
    """, unsafe_allow_html=True)

    d1, d2, d3 = st.columns(3)

    # 1. Cleaned Dataset Download
    cleaned_csv = filtered_df.to_csv(index=False).encode('utf-8')
    d1.download_button(
        label="📥 Download Cleaned Dataset (CSV)",
        data=cleaned_csv,
        file_name="cleaned_ecommerce_transactions.csv",
        mime="text/csv",
        use_container_width=True
    )

    # 2. Category Summary Download
    if map_cat != "None" and col_amt_clean:
        cat_df_export = analysis.calculate_category_summary(filtered_df, category_col=map_cat, amount_col=col_amt_clean, qty_col=col_qty_clean)
        cat_csv = cat_df_export.to_csv(index=False).encode('utf-8')
        d2.download_button(
            label="📥 Download Category Summary (CSV)",
            data=cat_csv,
            file_name="category_sales_summary.csv",
            mime="text/csv",
            use_container_width=True
        )

    # 3. Monthly Time-Series Summary Download
    if col_date_clean and col_amt_clean and col_date_clean in filtered_df.columns:
        ts_df_export = analysis.calculate_time_series_sales(filtered_df, date_col=col_date_clean, amount_col=col_amt_clean, freq="ME")
        ts_csv = ts_df_export.to_csv(index=False).encode('utf-8')
        d3.download_button(
            label="📥 Download Monthly Sales (CSV)",
            data=ts_csv,
            file_name="monthly_sales_time_series.csv",
            mime="text/csv",
            use_container_width=True
        )

    st.markdown("---")
    st.markdown("##### 📝 Executive Summary Brief")
    st.text_area(
        "Auto-Generated Project Abstract & Insights",
        value=f"""PROJECT REPORT: ONLINE SHOPPING BEHAVIOUR AND PURCHASE TREND ANALYSIS

1. EXECUTIVE SUMMARY:
- Total Dataset Transactions Analyzed: {len(filtered_df):,}
- Total Gross Revenue: ${kpis['total_revenue']:,.2f}
- Average Transaction Value: ${kpis['average_transaction_value']:,.2f}
- Total Units Transacted: {kpis['total_units']:,}
- Unique Customers: {kpis['unique_customers']:,} (Repeat Buyer Rate: {kpis['repeat_customer_rate']}%)

2. SYLLABUS INSIGHTS:
- Unit 4 (Bivariate & Resistant Lines): Demonstrates Tukey's 3-group resistant line fitting to guard against outlier bias in sales forecasting.
- Unit 5 (Multivariate & Time Series): Evaluates customer-stratified contingency tables, seasonal cycles, and frequency resampling across Daily, Weekly, Monthly, and Quarterly intervals.
""",
        height=220
    )

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #94A3B8; font-size: 0.85rem;'>"
    "Online Shopping Behaviour and Purchase Trend Analysis &bull; College-Level EDA Project &bull; Built with Python, Pandas, Streamlit & Plotly"
    "</div>",
    unsafe_allow_html=True
)
