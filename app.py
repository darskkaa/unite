import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

# --- PAGE SETUP ---
st.set_page_config(page_title="United Way Tracker", layout="wide")
st.title("💙 United Way Service Dashboard")

# --- DATABASE CONNECTION ---
# We get the password from the secret file (Phase 4)
try:
    db_url = st.secrets["db_url"]
    engine = create_engine(db_url)
except Exception as e:
    st.error(f"Database Connection Failed: {e}")
    st.stop()

# --- HELPER FUNCTION ---
def get_data(query):
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

# --- SIDEBAR FILTERS ---
st.sidebar.header("Filter Options")
selected_status = st.sidebar.selectbox("Filter by Status", ["All", "Open", "In Progress", "Closed"])

# --- DASHBOARD METRICS ---
col1, col2, col3 = st.columns(3)
with col1:
    total_reqs = get_data("SELECT COUNT(*) FROM ServiceRequests").iloc[0,0]
    st.metric("Total Requests", total_reqs)
with col2:
    open_reqs = get_data("SELECT COUNT(*) FROM ServiceRequests WHERE status='Open'").iloc[0,0]
    st.metric("Open Cases", open_reqs)
with col3:
    regions = get_data("SELECT COUNT(*) FROM Regions").iloc[0,0]
    st.metric("Active Regions", regions)

# --- MAIN CHARTS ---
st.subheader("📊 Service Demand by Region")
df_region = get_data("""
    SELECT r.region_name, COUNT(s.request_id) as count 
    FROM ServiceRequests s 
    JOIN Regions r ON s.region_id = r.region_id 
    GROUP BY r.region_name
""")
st.bar_chart(df_region.set_index("region_name"))

# --- DATA TABLE ---
st.subheader("📋 Recent Service Requests")
query = "SELECT * FROM ServiceRequests"
if selected_status != "All":
    query += f" WHERE status = '{selected_status}'"

df_requests = get_data(query)
st.dataframe(df_requests, use_container_width=True)

# --- NEW ENTRY FORM (Bonus Points) ---
with st.expander("➕ Log New Request (Simulation)"):
    with st.form("new_req"):
        st.write("This form simulates adding data.")
        type_input = st.text_input("Request Type")
        submitted = st.form_submit_button("Submit")
        if submitted:
            st.success(f"Request for '{type_input}' logged! (Demo Mode)")
