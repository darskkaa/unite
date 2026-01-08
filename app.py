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

def execute_query(query, params=None):
    with engine.connect() as conn:
        conn.execute(text(query), params or {})
        conn.commit()

# --- 1. KEY METRICS ---
col1, col2, col3, col4 = st.columns(4)
total_reqs = get_data("SELECT COUNT(*) FROM ServiceRequests").iloc[0,0]
open_cases = get_data("SELECT COUNT(*) FROM ServiceRequests WHERE status != 'Closed'").iloc[0,0]
staff_count = get_data("SELECT COUNT(*) FROM Staff").iloc[0,0]
# Requirement: "Patterns in follow-up completion"
completion_rate = get_data("""
    SELECT 
        ROUND(100.0 * SUM(CASE WHEN completion_status = 'Completed' THEN 1 ELSE 0 END) / COUNT(*), 1) 
    FROM FollowUps
""").iloc[0,0]

col1.metric("Total Requests", total_reqs)
col2.metric("Open Cases", open_cases)
col3.metric("Active Staff", staff_count)
col4.metric("Follow-Up Success Rate", f"{completion_rate}%")

# --- 2. ANALYTICS SECTION ---
st.markdown("---")
st.subheader("📊 Operational Analytics")
c1, c2 = st.columns(2)

with c1:
    st.caption("Service Demand by Region")
    df_region = get_data("""
        SELECT r.region_name, COUNT(s.request_id) as requests 
        FROM ServiceRequests s JOIN Regions r ON s.region_id = r.region_id 
        GROUP BY r.region_name
    """)
    st.bar_chart(df_region.set_index("region_name"))

with c2:
    # CLEANED TITLE (Removed the "MISSING FEATURE" text)
    st.caption("Staff Workload Distribution") 
    df_staff = get_data("""
        SELECT s.name, COUNT(f.followup_id) as tasks_assigned
        FROM Staff s JOIN FollowUps f ON s.staff_id = f.staff_id
        GROUP BY s.name
    """)
    st.bar_chart(df_staff.set_index("name"), color="#ffaa00")

# --- 3. DATA MANAGEMENT SECTION ---
st.markdown("---")
st.subheader("📋 Case Management Data")

# Requirement: "Generate summary reports" -> Download Button
df_export = get_data("SELECT * FROM ServiceRequests")
csv = df_export.to_csv(index=False).encode('utf-8')
st.download_button("📥 Download Summary Report (CSV)", data=csv, file_name="united_way_report.csv", mime="text/csv")

tab1, tab2 = st.tabs(["Incoming Requests", "Staff Follow-Ups"])

with tab1:
    st.dataframe(get_data("SELECT * FROM ServiceRequests ORDER BY request_date DESC"), use_container_width=True)

with tab2:
    st.dataframe(get_data("""
        SELECT f.followup_id, s.name as Staff, f.notes, f.completion_status, f.followup_date
        FROM FollowUps f 
        JOIN Staff s ON f.staff_id = s.staff_id
        ORDER BY f.followup_date DESC
    """), use_container_width=True)

# --- 4. SIDEBAR: FULL MANAGEMENT SUITE ---
st.sidebar.header("🛠️ Management Tools")
action = st.sidebar.selectbox("Choose Action", ["Log New Request", "Update Status", "Delete Record", "Assign Follow-Up"])

if action == "Log New Request":
    with st.sidebar.form("add_req"):
        st.subheader("New Request")
        rtype = st.selectbox("Type", ["Food Pantry", "Housing", "Utility", "Mental Health"])
        prio = st.select_slider("Priority", ["Low", "High", "Critical"])
        reg = st.selectbox("Region ID", [1, 2, 3, 4])
        if st.form_submit_button("Submit"):
            execute_query(
                "INSERT INTO ServiceRequests (region_id, request_type, status, priority) VALUES (:r, :t, 'Open', :p)",
                {"r": reg, "t": rtype, "p": prio}
            )
            st.success("Request Created!")
            st.rerun()

elif action == "Update Status":
    st.sidebar.subheader("Update Case Status")
    req_id = st.sidebar.number_input("Request ID to Update", min_value=1, step=1)
    new_stat = st.sidebar.selectbox("New Status", ["Open", "In Progress", "Closed"])
    if st.sidebar.button("Update Status"):
        execute_query("UPDATE ServiceRequests SET status = :s WHERE request_id = :id", {"s": new_stat, "id": req_id})
        st.success(f"Request {req_id} updated to {new_stat}!")
        st.rerun()

elif action == "Delete Record":
    st.sidebar.subheader("⚠️ Delete Task")
    del_id = st.sidebar.number_input("Request ID to Delete", min_value=1, step=1)
    st.sidebar.warning("This will also delete associated follow-ups.")
    if st.sidebar.button("Permanently Delete"):
        # Delete children first (Foreign Key constraint)
        execute_query("DELETE FROM FollowUps WHERE request_id = :id", {"id": del_id})
        # Then delete parent
        execute_query("DELETE FROM ServiceRequests WHERE request_id = :id", {"id": del_id})
        st.error(f"Request {del_id} Deleted.")
        st.rerun()

elif action == "Assign Follow-Up":
    with st.sidebar.form("followup"):
        st.subheader("Log Staff Action")
        rid = st.number_input("Request ID", min_value=1)
        sid = st.selectbox("Staff ID", [1, 2, 3])
        note = st.text_area("Notes")
        stat = st.selectbox("Outcome", ["Pending", "Completed", "Failed"])
        if st.form_submit_button("Submit Log"):
            execute_query(
                "INSERT INTO FollowUps (request_id, staff_id, notes, completion_status, followup_date) VALUES (:r, :s, :n, :c, CURRENT_DATE)",
                {"r": rid, "s": sid, "n": note, "c": stat}
            )
            st.success("Follow-up Logged!")
            st.rerun()
