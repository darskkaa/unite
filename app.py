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

# --- SMART LOOKUPS (For User Friendliness) ---
# Dictionary to map ID numbers to Real Names
REGION_MAP = {
    "East Lee County": 1,
    "Hendry County": 2,
    "Glades County": 3,
    "Downtown Fort Myers": 4
}

# Function to get a list of active requests formatted nicely
# Returns list like: ["5: Food Pantry (Open)", "6: Housing (Critical)"]
def get_request_options():
    df = get_data("SELECT request_id, request_type, status FROM ServiceRequests ORDER BY request_id DESC")
    if df.empty:
        return []
    # Create a nice string for the user to select
    return [f"{row['request_id']}: {row['request_type']} ({row['status']})" for index, row in df.iterrows()]

def get_staff_options():
    df = get_data("SELECT staff_id, name FROM Staff")
    return {row["name"]: row["staff_id"] for index, row in df.iterrows()}

# --- 1. KEY METRICS ---
col1, col2, col3, col4 = st.columns(4)
total_reqs = get_data("SELECT COUNT(*) FROM ServiceRequests").iloc[0,0]
open_cases = get_data("SELECT COUNT(*) FROM ServiceRequests WHERE status != 'Closed'").iloc[0,0]
staff_count = get_data("SELECT COUNT(*) FROM Staff").iloc[0,0]
completion_rate = get_data("""
    SELECT ROUND(100.0 * SUM(CASE WHEN completion_status = 'Completed' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) 
    FROM FollowUps
""").iloc[0,0]
completion_rate = 0 if pd.isna(completion_rate) else completion_rate # Handle empty data

col1.metric("Total Requests", total_reqs)
col2.metric("Open Cases", open_cases)
col3.metric("Active Staff", staff_count)
col4.metric("Follow-Up Success Rate", f"{completion_rate}%")

# --- 2. ANALYTICS ---
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
    st.caption("Staff Workload Distribution") 
    df_staff = get_data("""
        SELECT s.name, COUNT(f.followup_id) as tasks_assigned
        FROM Staff s JOIN FollowUps f ON s.staff_id = f.staff_id
        GROUP BY s.name
    """)
    st.bar_chart(df_staff.set_index("name"), color="#ffaa00")

# --- 3. DATA TABLES & EXPORT ---
st.markdown("---")
col_header, col_btn = st.columns([4,1])
col_header.subheader("📋 Case Management Data")
csv = get_data("SELECT * FROM ServiceRequests").to_csv(index=False).encode('utf-8')
col_btn.download_button("📥 Download CSV Report", data=csv, file_name="united_way_report.csv", mime="text/csv")

tab1, tab2 = st.tabs(["Incoming Requests", "Staff Follow-Ups"])
with tab1:
    st.dataframe(get_data("""
        SELECT s.request_id, r.region_name, s.request_type, s.status, s.priority, s.request_date 
        FROM ServiceRequests s JOIN Regions r ON s.region_id = r.region_id 
        ORDER BY s.request_date DESC
    """), use_container_width=True)
with tab2:
    st.dataframe(get_data("""
        SELECT f.followup_id, s.name as Staff, f.notes, f.completion_status, f.followup_date
        FROM FollowUps f JOIN Staff s ON f.staff_id = s.staff_id ORDER BY f.followup_date DESC
    """), use_container_width=True)

# --- 4. SIDEBAR: INTUITIVE TOOLS ---
st.sidebar.header("🛠️ Management Tools")
action = st.sidebar.selectbox("Choose Action", ["Log New Request", "Update Status", "Delete Record", "Assign Follow-Up"])

# Fetch lists for dropdowns (So user doesn't have to type IDs)
request_list = get_request_options()
staff_map = get_staff_options() # Returns {"Sarah": 1, "Bruce": 2}

if action == "Log New Request":
    with st.sidebar.form("add_req"):
        st.subheader("New Request")
        rtype = st.selectbox("Type", ["Food Pantry", "Housing", "Utility", "Mental Health"])
        prio = st.select_slider("Priority", ["Low", "High", "Critical"])
        # USER FRIENDLY: Select name "East Lee", code converts to ID 1
        reg_name = st.selectbox("Region", list(REGION_MAP.keys()))
        
        if st.form_submit_button("Submit"):
            reg_id = REGION_MAP[reg_name]
            execute_query(
                "INSERT INTO ServiceRequests (region_id, request_type, status, priority) VALUES (:r, :t, 'Open', :p)",
                {"r": reg_id, "t": rtype, "p": prio}
            )
            st.success("Request Created!")
            st.rerun()

elif action == "Update Status":
    st.sidebar.subheader("Update Case Status")
    if not request_list:
        st.sidebar.warning("No requests available.")
    else:
        # USER FRIENDLY: Select "5: Food Pantry" instead of typing "5"
        selected_req_str = st.sidebar.selectbox("Select Request", request_list)
        # Extract ID from string "5: Food Pantry..." -> 5
        req_id = int(selected_req_str.split(":")[0])
        
        new_stat = st.sidebar.selectbox("New Status", ["Open", "In Progress", "Closed"])
        if st.sidebar.button("Update Status"):
            execute_query("UPDATE ServiceRequests SET status = :s WHERE request_id = :id", {"s": new_stat, "id": req_id})
            st.success("Updated!")
            st.rerun()

elif action == "Delete Record":
    st.sidebar.subheader("⚠️ Delete Task")
    if not request_list:
        st.sidebar.warning("No requests available.")
    else:
        selected_req_str = st.sidebar.selectbox("Select Request to Delete", request_list)
        req_id = int(selected_req_str.split(":")[0])
        
        if st.sidebar.button("Permanently Delete"):
            execute_query("DELETE FROM FollowUps WHERE request_id = :id", {"id": req_id})
            execute_query("DELETE FROM ServiceRequests WHERE request_id = :id", {"id": req_id})
            st.error("Deleted.")
            st.rerun()

elif action == "Assign Follow-Up":
    with st.sidebar.form("followup"):
        st.subheader("Log Staff Action")
        if not request_list:
            st.warning("No requests available.")
            st.stop()
            
        selected_req_str = st.selectbox("Request", request_list)
        req_id = int(selected_req_str.split(":")[0])
        
        # USER FRIENDLY: Select "Sarah Connor" instead of typing ID
        staff_name = st.selectbox("Assign Staff", list(staff_map.keys()))
        staff_id = staff_map[staff_name]
        
        note = st.text_area("Notes")
        stat = st.selectbox("Outcome", ["Pending", "Completed", "Failed"])
        
        if st.form_submit_button("Submit Log"):
            execute_query(
                "INSERT INTO FollowUps (request_id, staff_id, notes, completion_status, followup_date) VALUES (:r, :s, :n, :c, CURRENT_DATE)",
                {"r": req_id, "s": staff_id, "n": note, "c": stat}
            )
            st.success("Follow-up Logged!")
            st.rerun()
