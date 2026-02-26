# -*- coding: utf-8 -*-
"""
Loan Application & Transaction Fraud Detection Dashboard
Built with Python and Streamlit
"""

import streamlit as st
import pandas as pd
import plotly.express as px

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Fraud Detection Dashboard", page_icon="🛡️", layout="wide")

# ================= LOGIN SYSTEM =================
USERS = {"admin": "1234"}

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

def login():
    st.title("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if USERS.get(username) == password:
            st.session_state["authenticated"] = True
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("Invalid username or password")

def logout():
    if st.sidebar.button("Logout"):
        st.session_state["authenticated"] = False
        st.rerun()

if not st.session_state["authenticated"]:
    login()
    st.stop()

logout()

# === SIDEBAR LOGO ===
st.sidebar.image("logo.png", width=200)

# ================= LOAD DATA =================
@st.cache_data
def load_data():
    loans = pd.read_csv("loan_applications_filtered.csv")
    txns = pd.read_csv("transactions.csv")

    loans["application_date"] = pd.to_datetime(loans["application_date"])
    if "transaction_date" in txns.columns:
        txns["transaction_date"] = pd.to_datetime(txns["transaction_date"])

    return loans, txns

loan_df, txn_df = load_data()

#=============State Extraction from transaction_location=============

# Create State column safely
if "transaction_location" in txn_df.columns:
    txn_df["State"] = txn_df["transaction_location"].astype(str).str.split(",").str[-1].str.strip()
else:
    st.error("transaction_location column not found in transactions.csv")
  
# ================= NAVIGATION =================
st.sidebar.title("📊 Navigation")

page = st.sidebar.radio(
    "Go to",
    ["Executive Loan Portfolio", "Fraud Intelligence & Risk Mitigation", "Behavioral Risk Analysis"]
)

# ================= SIDEBAR FILTERS =================
st.sidebar.title("🔍 Filters")

loan_type_filter = st.sidebar.multiselect("Loan Type", loan_df["loan_type"].unique())
employment_filter = st.sidebar.multiselect("Employment Status", loan_df["employment_status"].unique())
gender_filter = st.sidebar.multiselect("Gender", loan_df["gender"].unique())

device_filter = st.sidebar.multiselect("Device", txn_df["device_used"].unique())
state_filter = st.sidebar.multiselect("State", txn_df["State"].unique())

date_range = st.sidebar.date_input(
    "Application Date Range",
    [loan_df["application_date"].min(), loan_df["application_date"].max()]
)

# ================= APPLY FILTERS =================
filtered_loans = loan_df.copy()
filtered_txns = txn_df.copy()

if loan_type_filter:
    filtered_loans = filtered_loans[filtered_loans["loan_type"].isin(loan_type_filter)]

if employment_filter:
    filtered_loans = filtered_loans[filtered_loans["employment_status"].isin(employment_filter)]

if gender_filter:
    filtered_loans = filtered_loans[filtered_loans["gender"].isin(gender_filter)]

if device_filter:
    filtered_txns = filtered_txns[filtered_txns["device_used"].isin(device_filter)]

if state_filter:
    filtered_txns = filtered_txns[filtered_txns["State"].isin(state_filter)]

start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
filtered_loans = filtered_loans[
    (filtered_loans["application_date"] >= start_date) &
    (filtered_loans["application_date"] <= end_date)
]




# ==============================================================
# ================= Executive Loan Portfolio =================
if page == "Executive Loan Portfolio":
    st.title("📘 Executive Loan Portfolio")
    st.markdown("### High-Level Performance Metrics")

    # --- 1. Calculations ---
    total_apps = len(filtered_loans)
    grand_total_amount = filtered_loans['loan_amount_requested'].sum()
    avg_cibil = filtered_loans['cibil_score'].mean()
    approval_rate = (filtered_loans['loan_status'] == 'Approved').mean() * 100 if total_apps > 0 else 0
    avg_income = filtered_loans['monthly_income'].mean()

    # --- 2. KPI Metrics Row (Kept as 5 columns for top summary) ---
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Applications", f"{total_apps:,}")
    m2.metric("Total Requested", f"₹{grand_total_amount/1e7:.2f} Cr")
    m3.metric("Avg CIBIL Score", f"{avg_cibil:.0f}")
    m4.metric("Approval Rate", f"{approval_rate:.1f}%")
    m5.metric("Avg Monthly Income", f"₹{avg_income:,.0f}")

    st.markdown("---")

    # --- 3. Full Width Visuals (Columns Removed) ---

    # 1. Demand by Loan Type (% of Grand Total Amount)
    demand_grouped = filtered_loans.groupby(['loan_type', 'loan_status'])['loan_amount_requested'].sum().reset_index()
    demand_grouped['pct_of_total'] = (demand_grouped['loan_amount_requested'] / grand_total_amount) * 100

    fig_demand = px.bar(
        demand_grouped, 
        x="loan_type", 
        y="pct_of_total",
        color="loan_status", 
        title="Demand by Loan Type (% of Grand Total Amount)",
        text=demand_grouped['pct_of_total'].apply(lambda x: f'{x:.1f}%'),
        labels={'pct_of_total': '% of Total Requested', 'loan_type': 'Loan Category', 'loan_status': 'Status'},
        barmode='group'
    )
    fig_demand.update_traces(textposition='outside')
    st.plotly_chart(fig_demand, use_container_width=True)

    st.markdown("---")

    # 2. Applicant Age Demographics (% of Total Applicants)
    age_bins = [0, 25, 35, 45, 55, 100]
    age_labels = ['18-25', '26-35', '36-45', '46-55', '56+']
    filtered_loans['age_group'] = pd.cut(filtered_loans['applicant_age'], bins=age_bins, labels=age_labels)
    age_df = filtered_loans['age_group'].value_counts().reindex(age_labels).reset_index()
    age_df.columns = ['age_group', 'count']
    age_df['pct'] = (age_df['count'] / total_apps) * 100 if total_apps > 0 else 0

    fig_age = px.bar(
        age_df, 
        x="age_group", 
        y="pct",
        title="Applicant Age Demographics (% of Total Applicants)",
        color="age_group",
        text=age_df['pct'].apply(lambda x: f'{x:.1f}%'),
        labels={'age_group': 'Age Group', 'pct': '% of Applicants'},
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig_age.update_traces(textposition='outside')
    fig_age.update_yaxes(ticksuffix="%") 
    st.plotly_chart(fig_age, use_container_width=True)

    st.markdown("---")

    # 3. Approval Status Breakdown (Donut)
    status_df = filtered_loans['loan_status'].value_counts().reset_index()
    fig_status = px.pie(
        status_df, values='count', names='loan_status', 
        title="Approval Status Breakdown",
        hole=0.5,
        color_discrete_sequence=px.colors.qualitative.Safe
    )
    fig_status.update_traces(textinfo='percent+label')
    st.plotly_chart(fig_status, use_container_width=True)

    st.markdown("---")

    # 4. CIBIL Score vs. Income (Scatter)
    fig_scatter = px.scatter(
        filtered_loans, 
        x="cibil_score", 
        y="monthly_income",
        color="loan_status",
        title="CIBIL Score vs. Income Analysis",
        labels={"cibil_score": "CIBIL Score", "monthly_income": "Monthly Income"},
        opacity=0.5
    )
    st.plotly_chart(fig_scatter, use_container_width=True)






# ========================================================================
# ================= Fraud Intelligence & Risk Mitigation =================
# ================= Fraud Intelligence & Risk Mitigation =================
elif page == "Fraud Intelligence & Risk Mitigation":
    st.title("🛡️ Fraud Intelligence & Risk Mitigation")
    st.markdown("### High-Risk Activity & Pattern Analysis")

    # ------------------ PREP ------------------
    filtered_txns["State"] = (
        filtered_txns["transaction_location"]
        .str.split(",")
        .str[-1]
        .str.strip()
    )

    # DTI Risk Category (DAX SWITCH equivalent)
    def dti_category(x):
        if x < 20:
            return "Excellent (<20)"
        elif 20 <= x <= 35:
            return "Good (20–35)"
        elif 36 <= x <= 40:
            return "Fair (36–40)"
        elif 40 < x <= 100:
            return "High Risk (40–50)"
        else:
            return "Out of Range"

    filtered_loans["DTI_Risk_Category"] = (
        filtered_loans["debt_to_income_ratio"]
        .apply(dti_category)
    )

    # ------------------ KPI CALCULATIONS ------------------

    total_loan_apps = len(filtered_loans)
    total_txns = len(filtered_txns)

    fraud_loans = filtered_loans[filtered_loans["fraud_flag"] == 1]
    fraud_txns = filtered_txns[filtered_txns["fraud_flag"] == 1]

    total_fraud = len(fraud_loans)

    # 1️⃣ Total Fraud Rate (%)
    loan_fraud_rate = len(fraud_loans) / total_loan_apps if total_loan_apps else 0
    txn_fraud_rate = len(fraud_txns) / total_txns if total_txns else 0
    total_fraud_rate = (loan_fraud_rate + txn_fraud_rate) * 100

    # 2️⃣ Total Fraudulent Value
    total_fraud_value = (
        fraud_loans["loan_amount_requested"].sum() +
        fraud_txns["transaction_amount"].sum()
    )

    # 3️⃣ Detected & Undetected Fraud (%)
    detected_fraud = fraud_loans[
        fraud_loans["loan_status"] == "Fraudulent - detected"
    ]
    undetected_fraud = fraud_loans[
        fraud_loans["loan_status"] == "Fraudulent - Undetected"
    ]
   
    undetected_pct = (len(undetected_fraud) / total_fraud * 100) if total_fraud else 0

    # 4️⃣ Risk Density (per 1000 customers)
    total_customers = filtered_loans["customer_id"].nunique()
    risk_density = (total_fraud / total_customers) * 1000 if total_customers else 0

    # ------------------ KPI ROW ------------------
    k1, k2, k3, k4 = st.columns(4)

    k1.metric("Total Fraud Rate", f"{total_fraud_rate:.2f}%")
    k2.metric("Total Fraudulent Value", f"₹{total_fraud_value:,.0f}")
    k3.metric("Undetected Fraud (%)", f"{undetected_pct:.2f}%")
    k4.metric("Risk Density (per 1000)", f"{risk_density:.2f}")

    st.markdown("---")

    # ================= VISUALS =================

    # 1️⃣ Fraud by Employment Status (STACKED %)
    emp_fraud = (
        fraud_loans.groupby(["employment_status", "fraud_type"])
        .size()
        .reset_index(name="count")
    )
    emp_fraud["pct"] = (
        emp_fraud.groupby("employment_status")["count"]
        .transform(lambda x: x / x.sum() * 100)
    )

    fig_emp = px.bar(
        emp_fraud,
        x="employment_status",
        y="pct",
        color="fraud_type",
        text=emp_fraud["pct"].round(2).astype(str) + "%",
        title="Fraud by Employment Status (%)",
        labels={"pct": "% Loan Fraud"}
    )
    fig_emp.update_traces(textposition="inside")
    st.plotly_chart(fig_emp, use_container_width=True)

    # 2️⃣ DTI Risk Category vs Fraud (%)
    dti_fraud = (
        filtered_loans.groupby(["DTI_Risk_Category", "fraud_flag"])
        .size()
        .reset_index(name="count")
    )
    dti_fraud["pct"] = (
        dti_fraud.groupby("DTI_Risk_Category")["count"]
        .transform(lambda x: x / x.sum() * 100)
    )

    fig_dti = px.bar(
        dti_fraud,
        x="DTI_Risk_Category",
        y="pct",
        color="fraud_flag",
        text=dti_fraud["pct"].round(2).astype(str) + "%",
        title="DTI Risk Category vs Fraud (%)",
        labels={"pct": "% Loan Fraud"}
    )
    fig_dti.update_traces(textposition="outside")
    st.plotly_chart(fig_dti, use_container_width=True)

    # 3️⃣ Transaction Amount vs Fraud (PIE)
    txn_amt = (
        filtered_txns.groupby("fraud_flag")["transaction_amount"]
        .sum()
        .reset_index()
    )

    fig_txn_amt = px.pie(
        txn_amt,
        names="fraud_flag",
        values="transaction_amount",
        title="Transaction Amount vs Fraud",
        hole=0.4
    )
    st.plotly_chart(fig_txn_amt, use_container_width=True)

    # 4️⃣ Top 10 Fraudulent Transaction States (% of Transactions)
    state_fraud = (
        fraud_txns["State"]
        .value_counts(normalize=True)
        .head(10)
        .reset_index()
    )
    state_fraud.columns = ["State", "pct"]
    state_fraud["pct"] *= 100

    fig_state = px.bar(
        state_fraud,
        x="State",
        y="pct",
        text=state_fraud["pct"].round(2).astype(str) + "%",
        title="Top 10 Fraudulent Transaction States (%)",
        labels={"pct": "% Fraud Transactions"}
    )
    fig_state.update_traces(textposition="outside")
    st.plotly_chart(fig_state, use_container_width=True)

    # 5️⃣ Property Ownership vs Fraud (CLUSTERED COLUMN)
    prop_fraud = (
        filtered_loans.groupby(
            ["property_ownership_status", "fraud_flag"]
        )["customer_id"]
        .nunique()
        .reset_index(name="customer_count")
    )
    prop_fraud["pct"] = (
        prop_fraud.groupby("property_ownership_status")["customer_count"]
        .transform(lambda x: x / x.sum() * 100)
    )

    fig_prop = px.bar(
        prop_fraud,
        x="property_ownership_status",
        y="pct",
        color="fraud_flag",
        barmode="group",
        text=prop_fraud["pct"].round(2).astype(str) + "%",
        title="Property Ownership vs Fraud (%)",
        labels={"pct": "% Distinct Customers"}
    )
    fig_prop.update_traces(textposition="outside")
    st.plotly_chart(fig_prop, use_container_width=True)


#=================================================================
#=============Behavioral Risk Analysis Dashboard==============
elif page == "Behavioral Risk Analysis":
    st.title("🧠 Behavioral Risk Analysis")

    # ------------------ KPI CALCULATIONS ------------------
    total_transactions = len(filtered_txns)
    total_customers = filtered_txns["customer_id"].nunique()
    avg_transaction_value = filtered_txns["transaction_amount"].mean()
    success_rate = (filtered_txns[filtered_txns["fraud_flag"] == 0].shape[0] / total_transactions) * 100

    top_location = filtered_txns["transaction_location"].value_counts().idxmax()
    top_txn_type = filtered_txns["transaction_type"].value_counts().idxmax()

    # ------------------ KPI ROW ------------------
    k1, k2, k3, k4, k5, k6 = st.columns(6)

    k1.metric("Total Transaction", f"{total_transactions/1000:.2f}K")
    k2.metric("Total Customer", f"{total_customers/1000:.2f}K")
    k3.metric("Avg Transaction Value (ATV)", f"{avg_transaction_value/1000:.2f}K")
    k4.metric("Success Rate", f"{success_rate:.2f}%")
    k5.metric("Highest Transaction Location", top_location)
    k6.metric("Top Transaction Type", top_txn_type)

    st.markdown("---")

    # ------------------ VISUAL ROW 1 ------------------
    c1, c2, c3 = st.columns(3)

    # 1️⃣ Spending Heatmap by Category (using transaction_type)
    with c1:
        cat_spend = (
            filtered_txns.groupby("transaction_type")["transaction_amount"]
            .sum()
            .reset_index()
        )

        fig_cat = px.treemap(
            cat_spend,
            path=["transaction_type"],
            values="transaction_amount",
            title="Spending Heatmap by Category"
        )

        fig_cat.update_traces(textinfo="label+percent entry")
        

        st.plotly_chart(fig_cat, use_container_width=True)

    # 2️⃣ Device Risk Analysis (%)
    with c2:
        device_risk = (
            filtered_txns.groupby(["device_used", "fraud_flag"])
            .size()
            .reset_index(name="count")
        )

        device_risk["pct"] = device_risk.groupby("device_used")["count"].transform(
            lambda x: x / x.sum() * 100
        )

        fig_device = px.bar(
            device_risk,
            x="device_used",
            y="pct",
            color="fraud_flag",
            text=device_risk["pct"].round(2).astype(str) + "%",
            title="Device Risk Analysis (%)",
            labels={"pct": "Percentage (%)"}
        )
        fig_device.update_traces(textposition="outside")
        fig_device.update_yaxes(ticksuffix="%")
        st.plotly_chart(fig_device, use_container_width=True)

    # 3️⃣ International vs Domestic (% of Amount)
    with c3:
        intl_dom = (
            filtered_txns.groupby("is_international_transaction")["transaction_amount"]
            .sum()
            .reset_index()
        )

        intl_dom["pct"] = intl_dom["transaction_amount"] / intl_dom["transaction_amount"].sum() * 100

        fig_intl = px.bar(
            intl_dom,
            x="is_international_transaction",
            y="pct",
            text=intl_dom["pct"].round(2).astype(str) + "%",
            title="International vs Domestic (%)",
            labels={"pct": "Percentage (%)"}
        )
        fig_intl.update_traces(textposition="outside")
        fig_intl.update_yaxes(ticksuffix="%")
        st.plotly_chart(fig_intl, use_container_width=True)

    st.markdown("---")

    # ------------------ TRANSACTION VELOCITY (% by day) ------------------
    filtered_txns["transaction_date"] = pd.to_datetime(filtered_txns["transaction_date"])

    velocity = (
        filtered_txns.groupby(filtered_txns["transaction_date"].dt.day)["transaction_amount"]
        .sum()
        .reset_index()
    )

    velocity["pct"] = velocity["transaction_amount"] / velocity["transaction_amount"].sum() * 100

    fig_vel = px.area(
        velocity,
        x="transaction_date",
        y="pct",
        title="Transaction Velocity (%)",
        labels={"pct": "Percentage (%)"}
    )
    fig_vel.update_yaxes(ticksuffix="%")
    st.plotly_chart(fig_vel, use_container_width=True)

    st.markdown("---")

    # ------------------ BEHAVIORAL FRAUD ANALYSIS ------------------


    # 5️⃣ Fraud by Device (%)
    fraud_device = (
        filtered_txns.groupby(["device_used", "fraud_flag"])
        .size()
        .reset_index(name="count")
    )

    fraud_device["pct"] = fraud_device.groupby("device_used")["count"].transform(
        lambda x: x / x.sum() * 100
    )

    fig6 = px.bar(
        fraud_device,
        x="device_used",
        y="pct",
        color="fraud_flag",
        text=fraud_device["pct"].round(2).astype(str) + "%",
        title="Fraud by Device (%)",
        labels={"pct": "Percentage (%)"}
    )
    fig6.update_traces(textposition="outside")
    fig6.update_yaxes(ticksuffix="%")
    st.plotly_chart(fig6, use_container_width=True)

    # 6️⃣ Income vs Loan Amount (Fraud Highlighted)
    fig7 = px.scatter(
        filtered_loans,
        x="monthly_income",
        y="loan_amount_requested",
        color="fraud_flag",
        title="Income vs Loan Amount (Fraud Highlighted)"
    )
    st.plotly_chart(fig7, use_container_width=True)