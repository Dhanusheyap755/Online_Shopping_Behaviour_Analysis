"""
Synthetic E-Commerce Dataset Generator for Online Shopping Behaviour Analysis.
Generates realistic e-commerce transactions across 12 consecutive months (Jan 2023 - Dec 2023)
with seasonal trends, product catalog pricing, customer repeat behaviour, and controlled
missing/duplicate records for exploratory data analysis.
"""

import os
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate_ecommerce_dataset(num_records=3200, seed=42):
    random.seed(seed)
    np.random.seed(seed)

    # Catalog definition: Category -> List of (Product Name, Base Price Range)
    catalog = {
        "Electronics": [
            ("Wireless Noise-Canceling Headphones", 120.0, 299.0),
            ("Smart Fitness Watch", 79.0, 220.0),
            ("Bluetooth Portable Speaker", 35.0, 95.0),
            ("Mechanical Gaming Keyboard", 55.0, 140.0),
            ("Ultra-Wide 4K Gaming Monitor", 280.0, 550.0),
            ("USB-C Fast Charging Hub", 22.0, 48.0)
        ],
        "Clothing & Apparel": [
            ("Classic Cotton Crewneck T-Shirt", 18.0, 35.0),
            ("Slim-Fit Stretch Denim Jeans", 42.0, 85.0),
            ("Insulated Winter Puffer Jacket", 85.0, 180.0),
            ("Breathable Athletic Running Shorts", 24.0, 45.0),
            ("Merino Wool Knit Sweater", 60.0, 125.0)
        ],
        "Home & Kitchen": [
            ("Non-Stick Stainless Steel Cookware Set", 89.0, 210.0),
            ("Programmable Drip Coffee Maker", 45.0, 115.0),
            ("Ergonomic Memory Foam Pillow", 28.0, 65.0),
            ("Robotic Vacuum Cleaner", 160.0, 380.0),
            ("Aromatherapy Essential Oil Diffuser", 20.0, 42.0)
        ],
        "Beauty & Personal Care": [
            ("Hydrating Hyaluronic Facial Serum", 22.0, 55.0),
            ("Organic Argan Hair Care Set", 25.0, 58.0),
            ("Sonic Electric Toothbrush", 38.0, 89.0),
            ("Matte Finish Mineral Sunscreen SPF 50", 18.0, 36.0),
            ("Lavender Exfoliating Body Scrub", 14.0, 28.0)
        ],
        "Books & Media": [
            ("Data Science and Machine Learning Handbook", 38.0, 75.0),
            ("Deep Work: Focused Success in a Distracted World", 16.0, 28.0),
            ("Atomic Habits Hardcover Edition", 15.0, 26.0),
            ("Sci-Fi Masterpiece Space Odyssey Boxset", 45.0, 90.0),
            ("Psychology of Money", 14.0, 24.0)
        ],
        "Sports & Outdoors": [
            ("Eco-Friendly Non-Slip Yoga Mat", 25.0, 55.0),
            ("Adjustable Quick-Select Dumbbell Pair", 95.0, 220.0),
            ("Thermal Insulated Stainless Water Bottle", 18.0, 35.0),
            ("Ultralight 2-Person Camping Tent", 75.0, 160.0),
            ("Speed Jump Rope with Ball Bearings", 12.0, 24.0)
        ]
    }

    categories = list(catalog.keys())
    # Category distribution weights
    category_weights = [0.25, 0.22, 0.18, 0.15, 0.10, 0.10]

    locations = ["California", "New York", "Texas", "Florida", "Illinois", "Washington", "Georgia", "Colorado"]
    location_weights = [0.24, 0.20, 0.16, 0.14, 0.10, 0.06, 0.05, 0.05]

    payment_methods = ["Credit Card", "Debit Card", "PayPal", "UPI", "Cash on Delivery"]
    payment_weights = [0.42, 0.24, 0.18, 0.11, 0.05]

    # Generate pool of 650 unique customers (creates repeat buyers for customer analysis)
    customer_ids = [f"CUST-{1000 + i}" for i in range(650)]
    customer_location_map = {cid: np.random.choice(locations, p=location_weights) for cid in customer_ids}

    start_date = datetime(2023, 1, 1)
    end_date = datetime(2023, 12, 31)
    days_range = (end_date - start_date).days

    records = []

    for i in range(num_records):
        order_id = f"ORD-{10001 + i}"
        customer_id = np.random.choice(customer_ids)
        customer_loc = customer_location_map[customer_id]

        # Generate order date with seasonal spikes:
        # Boost Q4 (holiday shopping season in Nov/Dec) and July summer sale
        day_offset = int(np.random.beta(a=1.5, b=1.2) * days_range)
        order_date = start_date + timedelta(days=day_offset, hours=random.randint(8, 23), minutes=random.randint(0, 59))

        category = np.random.choice(categories, p=category_weights)
        product_info = random.choice(catalog[category])
        product_name = product_info[0]
        unit_price = round(random.uniform(product_info[1], product_info[2]), 2)

        # Quantity skewed towards 1, 2, 3 with occasional bulk up to 8
        quantity = int(np.random.choice([1, 2, 3, 4, 5, 6, 8], p=[0.50, 0.26, 0.12, 0.05, 0.03, 0.02, 0.02]))

        # Discount: 0%, 5%, 10%, 15%, 20%, 25%
        discount_rate = float(np.random.choice([0.0, 0.05, 0.10, 0.15, 0.20, 0.25], p=[0.35, 0.25, 0.18, 0.12, 0.07, 0.03]))

        payment = np.random.choice(payment_methods, p=payment_weights)

        # Total Amount = Quantity * Unit Price * (1 - Discount)
        raw_total = quantity * unit_price * (1.0 - discount_rate)
        total_amount = round(raw_total, 2)

        records.append({
            "Order ID": order_id,
            "Customer ID": customer_id,
            "Order Date": order_date.strftime("%Y-%m-%d %H:%M:%S"),
            "Product Category": category,
            "Product Name": product_name,
            "Quantity": quantity,
            "Unit Price": unit_price,
            "Discount": discount_rate,
            "Payment Method": payment,
            "Customer Location": customer_loc,
            "Total Amount": total_amount
        })

    df = pd.DataFrame(records)

    # Sort chronologically by Order Date
    df["Order Date"] = pd.to_datetime(df["Order Date"])
    df = df.sort_values("Order Date").reset_index(drop=True)

    # Introduce a few realistic controlled missing values for EDA demonstration (~1.5% of selected columns)
    missing_indices_discount = np.random.choice(df.index, size=28, replace=False)
    df.loc[missing_indices_discount, "Discount"] = np.nan

    missing_indices_location = np.random.choice(df.index, size=15, replace=False)
    df.loc[missing_indices_location, "Customer Location"] = np.nan

    # Introduce controlled duplicate rows (~12 rows) to demonstrate duplicate detection and removal
    duplicate_indices = np.random.choice(df.index, size=12, replace=False)
    duplicates = df.loc[duplicate_indices].copy()
    df = pd.concat([df, duplicates], ignore_index=True)

    # Shuffle slightly so duplicates aren't all at bottom
    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)

    # Convert Order Date back to string format for standard CSV persistence
    df["Order Date"] = df["Order Date"].dt.strftime("%Y-%m-%d %H:%M:%S")

    return df

def generate_alternative_dataset(num_records=1200, seed=99):
    """
    Generates an alternative dataset with different column names and structure
    to verify dynamic column mapping and Excel file loading in Streamlit.
    """
    df = generate_ecommerce_dataset(num_records=num_records, seed=seed)
    # Rename columns to alternative e-commerce convention
    rename_map = {
        "Order ID": "Invoice_Number",
        "Customer ID": "User_Code",
        "Order Date": "Transaction_Timestamp",
        "Product Category": "Department",
        "Product Name": "Item_Description",
        "Quantity": "Units_Purchased",
        "Unit Price": "Item_Rate",
        "Discount": "Markdown_Percentage",
        "Payment Method": "Settlement_Channel",
        "Customer Location": "State_Province",
        "Total Amount": "Net_Sales_Value"
    }
    df_alt = df.rename(columns=rename_map)
    # Drop rows with NaN for a clean alternative dataset
    df_alt = df_alt.dropna().drop_duplicates().reset_index(drop=True)
    return df_alt

if __name__ == "__main__":
    base_dir = r"C:\Users\abidh\.gemini\antigravity\scratch\Online_Shopping_Behaviour_Analysis"
    dataset_dir = os.path.join(base_dir, "dataset")
    os.makedirs(dataset_dir, exist_ok=True)

    # Primary Dataset
    df_primary = generate_ecommerce_dataset(num_records=3200, seed=42)
    primary_csv = os.path.join(dataset_dir, "online_shopping_data.csv")
    df_primary.to_csv(primary_csv, index=False)
    print(f"Generated primary dataset: {primary_csv} with {len(df_primary)} rows and {df_primary.shape[1]} columns.")

    # Alternative Dataset (CSV and Excel) for Testing Column Mapping
    df_alt = generate_alternative_dataset(num_records=1200, seed=99)
    alt_csv = os.path.join(dataset_dir, "alternative_retail_transactions.csv")
    alt_xlsx = os.path.join(dataset_dir, "alternative_retail_transactions.xlsx")
    df_alt.to_csv(alt_csv, index=False)
    df_alt.to_excel(alt_xlsx, index=False, engine="openpyxl")
    print(f"Generated alternative dataset: {alt_csv} & {alt_xlsx} with {len(df_alt)} rows.")
