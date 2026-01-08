import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# --- PAGE CONFIG ---
st.set_page_config(page_title="United Way Service Dashboard", layout="wide")
st.title("💙 United Way Service Dashboard")

# --- DATABASE CONNECTION ---
try:
    db_url = st.secrets["db_url"]
    engine = create_engine(db_url)
except Exception as e:
    st.error(f"Database Connection Failed: {e}")
    st.stop()

# --- HELPER FUNCTIONS ---
def get_data(query):
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

def add_request(region_id, req_type, priority):
    with engine.connect() as conn:
        query = text("INSERT INTO ServiceRequests (region_id, request_type, status, priority) VALUES (:r, :t, 'Open', :p)")
        conn.execute(query, {"r": region_id, "t": req_type, "p": priority})
        conn.commit()

# --- 1. KEY METRICS (Existing + New) ---
col1, col2, col3 = st.columns(3)
total_reqs = get_data("SELECT COUNT(*) FROM ServiceRequests").iloc[0,0]
# New Metric: Staff Count
staff_count = get_data("SELECT COUNT(*) FROM Staff").iloc[0,0]
# New Metric: Pending Follow-Ups
pending_actions = get_data("SELECT COUNT(*) FROM FollowUps WHERE completion_status = 'Pending'").iloc[0,0]

col1.metric("Total Requests", total_reqs)
col2.metric("Active Staff", staff_count)
col3.metric("Pending Actions", pending_actions)

# --- 2. THE MISSING ANALYTICS (Requirement: Resource Allocation & Patterns) ---
st.markdown("---")
st.subheader("📊 Operational Analytics")
c1, c2 = st.columns(2)

with c1:
    st.caption("Service Demand by Region (Existing)")
    df_region = get_data("""
        SELECT r.region_name, COUNT(s.request_id) as requests 
        FROM ServiceRequests s JOIN Regions r ON s.region_id = r.region_id 
        GROUP BY r.region_name
    """)
    st.bar_chart(df_region.set_index("region_name"))

with c2:
    st.caption("Resource Allocation (Staff Workload) - **MISSING FEATURE FIXED**")
    # This answers "Resource allocation optimization"
    df_staff = get_data("""
        SELECT s.name, COUNT(f.followup_id) as tasks_assigned
        FROM Staff s JOIN FollowUps f ON s.staff_id = f.staff_id
        GROUP BY s.name
    """)
    st.bar_chart(df_staff.set_index("name"), color="#ffaa00")

# --- 3. DATA TABLES (Requirement: Track Follow-Ups) ---
st.markdown("---")
st.subheader("📋 Case Management Data")

tab1, tab2 = st.tabs(["Incoming Requests", "Staff Follow-Ups"])

with tab1:
    # This matches your current screenshot
    st.dataframe(get_data("SELECT * FROM ServiceRequests ORDER BY request_date DESC LIMIT 10"), use_container_width=True)

with tab2:
    # This answers "Store service requests AND follow-ups"
    st.write("**Follow-Up Activity Log (The Missing Piece)**")
    df_follow = get_data("""
        SELECT f.followup_id, s.name as Staff, f.notes, f.completion_status, f.followup_date
        FROM FollowUps f 
        JOIN Staff s ON f.staff_id = s.staff_id
        ORDER BY f.followup_date DESC
    """)
    st.dataframe(df_follow, use_container_width=True)

# --- 4. DATA ENTRY FORM ---
with st.sidebar.expander("➕ Log New Request"):
    with st.form("add_req"):
        rtype = st.selectbox("Type", ["Food Pantry", "Housing", "Utility"])
        prio = st.select_slider("Priority", ["Low", "High", "Critical"])
        reg = st.selectbox("Region", [1, 2, 3, 4])
        if st.form_submit_button("Submit"):
            add_request(reg, rtype, prio)
            st.success("Saved!")
            st.rerun()
