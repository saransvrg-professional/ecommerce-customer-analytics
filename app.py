# app.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO

st.set_page_config(page_title="E-Commerce Segments Dashboard", layout="wide")

st.title("E-Commerce Analytics — RFM & Segments")
st.write("Simple dashboard: upload transaction CSV or load saved customer segments.")

# --- Helper functions -------------------------------------------------------

def read_transactions(uploaded_file):
    """Try read csv or excel file into dataframe."""
    if uploaded_file is None:
        return None, "No file provided"
    name = uploaded_file.name.lower()
    try:
        if name.endswith(".csv"):
            df = pd.read_csv(uploaded_file, encoding='latin1')
        elif name.endswith(".xlsx") or name.endswith(".xls"):
            df = pd.read_excel(uploaded_file)
        else:
            return None, "Unsupported file type. Use CSV or Excel."
        return df, None
    except Exception as e:
        return None, str(e)

def compute_rfm(df):
    """Expect df with InvoiceNo, InvoiceDate, Quantity, UnitPrice, CustomerID"""
    df = df.copy()
    # clean column names
    df.columns = [c.replace('\ufeff','').strip() for c in df.columns]
    # parse dates
    for c in df.columns:
        if "date" in c.lower():
            df[c] = pd.to_datetime(df[c], errors='coerce', dayfirst=True)
    # ensure TotalPrice
    if "TotalPrice" not in df.columns:
        if "Quantity" in df.columns and "UnitPrice" in df.columns:
            df["TotalPrice"] = df["Quantity"] * df["UnitPrice"]
    # drop bad rows
    if "CustomerID" in df.columns:
        df = df[df["CustomerID"].notna()]
    if "InvoiceDate" in df.columns:
        df = df[df["InvoiceDate"].notna()]
    # snapshot date
    dt_col = [c for c in df.columns if np.issubdtype(df[c].dtype, np.datetime64)][0]
    snapshot = df[dt_col].max() + pd.Timedelta(days=1)
    rfm = df.groupby('CustomerID').agg({
        dt_col: lambda x: (snapshot - x.max()).days,
        'InvoiceNo': 'nunique',
        'TotalPrice': 'sum'
    }).reset_index()
    rfm.columns = ['CustomerID','Recency','Frequency','Monetary']
    # scores
    try:
        rfm['R_score'] = pd.qcut(rfm['Recency'],5, labels=[5,4,3,2,1]).astype(int)
        rfm['F_score'] = pd.qcut(rfm['Frequency'].rank(method='first'),5, labels=[1,2,3,4,5]).astype(int)
        rfm['M_score'] = pd.qcut(rfm['Monetary'],5, labels=[1,2,3,4,5]).astype(int)
    except Exception:
        # fallback if qcut fails
        rfm['R_score'] = pd.qcut(rfm['Recency'].rank(method='first'),5, labels=[5,4,3,2,1]).astype(int)
        rfm['F_score'] = pd.qcut(rfm['Frequency'].rank(method='first'),5, labels=[1,2,3,4,5]).astype(int)
        rfm['M_score'] = pd.qcut(rfm['Monetary'].rank(method='first'),5, labels=[1,2,3,4,5]).astype(int)
    rfm['RFM_Score'] = rfm['R_score'].astype(str) + rfm['F_score'].astype(str) + rfm['M_score'].astype(str)
    rfm['RFM_Sum'] = rfm['R_score'] + rfm['F_score'] + rfm['M_score']
    return rfm

def make_cluster_summary(rfm_df):
    summary = rfm_df.groupby('Cluster').agg({
        'Recency':'mean','Frequency':'mean','Monetary':'mean','CustomerID':'count'
    }).rename(columns={'CustomerID':'Count'})
    return summary

def to_csv_bytes(df):
    b = BytesIO()
    df.to_csv(b, index=False)
    b.seek(0)
    return b

def generate_messages(segment_name, example_name="{{Name}}", tone="friendly"):
    """Create 3 short templates for Email, SMS, WhatsApp."""
    if segment_name == "VIP":
        email = (f"Subject: Thank you {example_name} — VIP Offer\n\n"
                 f"Hi {example_name},\nThank you for being a top customer. Enjoy an exclusive 20% off on your next order. Code: VIP20.\nWe truly value you.")
        sms = f"Hi {example_name}, VIP 20% OFF for you. Use VIP20. Thank you!"
        wa = f"Hi {example_name} 👑 VIP Discount: 20% off with VIP20. Thank you for being with us!"
    elif segment_name == "Loyal":
        email = (f"Subject: Special for you {example_name}\n\n"
                 f"Hi {example_name}, thanks for shopping often! Use LOYAL15 for 15% off and early access to new arrivals.")
        sms = f"Hi {example_name}, enjoy 15% off with LOYAL15. Thank you!"
        wa = f"Hi {example_name}, you've got 15% off (LOYAL15). Check new products now!"
    elif segment_name == "Regular":
        email = (f"Subject: We miss you {example_name}\n\n"
                 f"Hi {example_name}, we added new products. Use BACK10 to get 10% off on your next purchase.")
        sms = f"Hi {example_name}, 10% off with BACK10. See what's new!"
        wa = f"Hi {example_name}, 10% BACK10 — new arrivals waiting for you."
    else:  # At-Risk
        email = (f"Subject: Come back {example_name} — 20% off\n\n"
                 f"Hi {example_name}, we miss you. Here's 20% off for the next 48 hours. Use WELCOME20.")
        sms = f"Hi {example_name}, we miss you — 20% OFF WELCOME20. 48hrs only."
        wa = f"Hi {example_name}, comeback offer 20% OFF (WELCOME20). Hurry!"
    return {"email": email, "sms": sms, "wa": wa}

# --- Sidebar: load or upload ------------------------------------------------
st.sidebar.header("Data input")
option = st.sidebar.selectbox("Choose data source", ("Load saved segments", "Upload transactions CSV"))

df_source = None
rfm_df = None

if option == "Load saved segments":
    saved_path = st.sidebar.text_input("Saved segments CSV path", 
                                      value=r"C:\Users\saran_boa\OneDrive\Desktop\ecommerce_ai_project\customer_segments.csv")
    if st.sidebar.button("Load saved CSV"):
        try:
            df_source = pd.read_csv(saved_path)
            st.success("Loaded saved customer segments CSV.")
        except Exception as e:
            st.error("Failed to load saved CSV: " + str(e))
else:
    uploaded = st.sidebar.file_uploader("Upload transactions CSV or Excel", type=["csv","xlsx","xls"])
    if uploaded is not None:
        df_temp, err = read_transactions(uploaded)
        if err:
            st.sidebar.error(err)
        else:
            st.sidebar.success("Transaction file read. Computing RFM...")
            try:
                rfm_df = compute_rfm(df_temp)
                # we will use rfm_df as df_source (clusters may not exist yet)
                df_source = rfm_df.copy()
                st.sidebar.success("RFM computed from uploaded file.")
            except Exception as e:
                st.sidebar.error("Error computing RFM: " + str(e))

# --- Main display -----------------------------------------------------------
st.markdown("---")
col1, col2 = st.columns([2,1])

with col1:
    st.header("Customer segments table")
    if df_source is None:
        st.info("No data loaded. Use sidebar to load saved segments or upload transactions.")
    else:
        st.dataframe(df_source.head(20))

        # If uploaded transactions produced RFM (no cluster), let user run a simple kmeans
        if 'Cluster' not in df_source.columns and 'Recency' in df_source.columns:
            st.warning("This data has RFM but no Cluster. You can run KMeans here.")
            k = st.number_input("Choose number of clusters (K)", min_value=2, max_value=8, value=4, step=1)
            if st.button("Run KMeans clustering"):
                # run simple KMeans
                from sklearn.cluster import KMeans
                from sklearn.preprocessing import StandardScaler
                X = df_source[['Recency','Frequency','Monetary']]
                scaler = StandardScaler()
                Xs = scaler.fit_transform(X)
                model = KMeans(n_clusters=int(k), random_state=42, n_init=10)
                df_source['Cluster'] = model.fit_predict(Xs)
                st.success("KMeans done. You can download the results.")
                rfm_df = df_source.copy()

        # If clusters exist already, show summary
        if 'Cluster' in df_source.columns:
            st.markdown("### Cluster summary (first rows)")
            st.write(df_source[['CustomerID','Recency','Frequency','Monetary','Cluster']].head(10))

with col2:
    st.header("Controls")
    if df_source is not None:
        if 'Cluster' in df_source.columns:
            # show cluster summary
            st.subheader("Cluster summary")
            summary = df_source.groupby('Cluster').agg({'Recency':'mean','Frequency':'mean','Monetary':'mean','CustomerID':'count'}).rename(columns={'CustomerID':'Count'})
            st.table(summary)
            # map cluster to friendly names automatically (simple logic)
            # determine which cluster has highest Monetary mean -> VIP
            vip_cluster = int(summary['Monetary'].idxmax())
            low_cluster = int(summary['Recency'].idxmax())  # largest recency => at-risk
            st.write(f"Auto labels: VIP = {vip_cluster}, At-risk = {low_cluster}")
            # allow download
            csv_bytes = to_csv_bytes(df_source)
            st.download_button("Download segments CSV", data=csv_bytes, file_name="customer_segments.csv", mime="text/csv")
        else:
            st.info("No clusters yet. Run KMeans or load saved segments.")

# --- Charts (full width) ----------------------------------------------------
st.markdown("---")
st.header("Charts")
if df_source is None:
    st.info("No data to plot.")
else:
    # if rfm_df exists use it, else build one if possible
    plot_df = df_source.copy()
    # simple histograms
    colA, colB, colC = st.columns(3)
    with colA:
        st.subheader("Recency distribution")
        fig1, ax1 = plt.subplots(figsize=(4,3))
        ax1.hist(plot_df['Recency'], bins=40)
        st.pyplot(fig1)
    with colB:
        st.subheader("Frequency distribution")
        fig2, ax2 = plt.subplots(figsize=(4,3))
        ax2.hist(plot_df['Frequency'], bins=40)
        st.pyplot(fig2)
    with colC:
        st.subheader("Monetary distribution")
        fig3, ax3 = plt.subplots(figsize=(4,3))
        ax3.hist(plot_df['Monetary'], bins=40)
        st.pyplot(fig3)

    # cluster pie if exists
    if 'Cluster' in plot_df.columns:
        st.subheader("Cluster distribution")
        fig4, ax4 = plt.subplots(figsize=(6,4))
        plot_df['Cluster'].value_counts().plot(kind='pie', autopct='%1.1f%%', ax=ax4)
        ax4.set_ylabel("")
        st.pyplot(fig4)

# --- Message generator ------------------------------------------------------
st.markdown("---")
st.header("Generate marketing messages")
if df_source is None or 'Cluster' not in df_source.columns:
    st.info("Load segmented CSV or run clustering to use message generator.")
else:
    cluster_select = st.selectbox("Pick cluster to generate messages", sorted(df_source['Cluster'].unique()))
    # auto map cluster label to friendly name using earlier heuristic
    summary = make_cluster_summary(df_source)
    vip_cluster = int(summary['Monetary'].idxmax())
    high_recency_cluster = int(summary['Recency'].idxmax())
    # determine name
    if cluster_select == vip_cluster:
        seg_name = "VIP"
    elif cluster_select == high_recency_cluster:
        seg_name = "At-Risk"
    else:
        # choose between Loyal and Regular by Frequency mean
        freq_med = summary.loc[cluster_select,'Frequency']
        seg_name = "Loyal" if freq_med > summary['Frequency'].median() else "Regular"

    st.write(f"Segment name (auto): **{seg_name}**")
    example_name = st.text_input("Example customer name (for templates)", value="Customer")
    msgs = generate_messages(seg_name, example_name)
    st.subheader("Email template")
    st.code(msgs['email'])
    st.subheader("SMS template")
    st.code(msgs['sms'])
    st.subheader("WhatsApp template")
    st.code(msgs['wa'])

st.markdown("---")
st.write("App created for your capstone. If you want, I can help convert this to a multi-page app or add LLM-based personalized messages next.")
