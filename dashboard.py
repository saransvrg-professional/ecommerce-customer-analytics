# dashboard.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="E-Commerce Customer Dashboard", layout="wide")

st.title("E-Commerce Customer Value Dashboard")
st.write("Clean RFM + KMeans segments — interactive dashboard for analysis.")

@st.cache_data
def load_data(path):
    df = pd.read_csv(path)
    return df

# Sidebar path input
path_input = st.sidebar.text_input("Segments CSV path",
                                  value=r"C:\Users\saran_boa\OneDrive\Desktop\ecommerce_ai_project\customer_segments.csv")

if st.sidebar.button("Load CSV"):
    try:
        df = load_data(path_input)
        st.sidebar.success("Loaded file successfully.")
    except Exception as e:
        st.sidebar.error("Failed to load CSV: " + str(e))
        st.stop()
else:
    st.info("Click 'Load CSV' in sidebar to load customer segments.")
    st.stop()

# Filters
st.sidebar.header("Filters")
clusters = sorted(df['Cluster'].unique().tolist())
sel_clusters = st.sidebar.multiselect("Select cluster(s)", options=clusters, default=clusters)
min_monetary = st.sidebar.number_input("Minimum Monetary Value", value=int(df['Monetary'].min()), step=100)

# Apply filters
df_filtered = df[(df['Cluster'].isin(sel_clusters)) & (df['Monetary'] >= min_monetary)]

# KPI metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Customers", f"{df_filtered['CustomerID'].nunique():,}")
with col2:
    st.metric("Avg Recency (days)", f"{df_filtered['Recency'].mean():.1f}")
with col3:
    st.metric("Avg Frequency", f"{df_filtered['Frequency'].mean():.2f}")
with col4:
    st.metric("Total Revenue (Monetary)", f"₹ {df_filtered['Monetary'].sum():,.0f}")

st.markdown("---")

# Cluster Distribution
colA, colB = st.columns([2,3])

with colA:
    st.subheader("Cluster Counts")
    count_df = df_filtered['Cluster'].value_counts().sort_index()
    st.bar_chart(count_df)

with colB:
    st.subheader("Cluster Summary")
    summary = df_filtered.groupby('Cluster').agg({'Recency':'mean','Frequency':'mean','Monetary':'mean','CustomerID':'count'})
    summary = summary.rename(columns={'CustomerID': 'Count'})
    st.dataframe(summary.style.format({"Recency": "{:.1f}", "Frequency": "{:.1f}", "Monetary": "{:.0f}", "Count": "{:,}"}))

st.markdown("---")

# Histograms & Scatter plots
colx, coly = st.columns(2)

with colx:
    st.subheader("Recency Distribution")
    fig1, ax1 = plt.subplots(figsize=(6, 3))
    ax1.hist(df_filtered['Recency'], bins=40, color="skyblue")
    ax1.set_xlabel("Recency")
    st.pyplot(fig1)

    st.subheader("Monetary Distribution (clipped top 1%)")
    fig2, ax2 = plt.subplots(figsize=(6, 3))
    ax2.hist(df_filtered['Monetary'].clip(0, df_filtered['Monetary'].quantile(0.99)), bins=40, color="orange")
    ax2.set_xlabel("Monetary")
    st.pyplot(fig2)

with coly:
    st.subheader("Frequency Distribution")
    fig3, ax3 = plt.subplots(figsize=(6, 3))
    ax3.hist(df_filtered['Frequency'], bins=30, color="green")
    ax3.set_xlabel("Frequency")
    st.pyplot(fig3)

    st.subheader("Frequency vs Monetary (Cluster)")
    fig4, ax4 = plt.subplots(figsize=(6, 3))
    scatter = ax4.scatter(df_filtered['Frequency'], df_filtered['Monetary'], c=df_filtered['Cluster'], cmap='cool')
    ax4.set_xlabel("Frequency")
    ax4.set_ylabel("Monetary")
    st.pyplot(fig4)

st.markdown("---")

# Top Customers
st.subheader("Top Customers by Monetary")
n = st.slider("Show top N customers", 5, 100, 10)
top_customers = df_filtered.sort_values('Monetary', ascending=False).head(n)

st.table(top_customers[['CustomerID','Cluster','Recency','Frequency','Monetary','RFM_Score']])

# Download filtered file
csv_export = df_filtered.to_csv(index=False).encode('utf-8')
st.download_button("Download Filtered CSV", data=csv_export, file_name="filtered_segments.csv", mime="text/csv")

st.markdown("---")
st.write("Dashboard ready. Export screenshots for LinkedIn or GitHub portfolio.")
