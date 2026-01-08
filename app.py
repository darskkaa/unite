import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta

# ==========================================
# 1. CONFIGURATION & PROFESSIONAL STYLING
# ==========================================
st.set_page_config(
    page_title="United Way Service Portal",
    page_icon="UW",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for a SOTA / Enterprise Look
st.markdown("""
    <style>
    /* Global Font & Background */
    .stApp {
        background-color: #f4f6f9;
    }
    
    /* Metrics Cards */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #102a5c; /* United Way Navy */
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-weight: 600;
    }
    
    /* Buttons */
    .stButton>button {
        color: white;
        background-color: #ff8200; /* United Way Orange */
        border: none;
        border-radius: 4px;
        padding: 0.5rem 1rem;
        font-weight: 500;
    }
    .stButton>button:hover {
        background-color: #e67600;
        border-color: #e67600;
        color: white;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e0e0e0;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px 4px 0px 0px;
        color: #4a4a4a;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: transparent;
        color: #102a5c;
        border-bottom: 2px solid #102a5c;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. DATABASE & HELPERS
# ==========================================
try:
    db_url = st.secrets["db_url"]
    engine = create_engine(db_url)
except Exception as e:
    st.error(f"Database Connection Error. Please check your configuration.")
    st.stop()

def run_query(query, params=None):
    with engine.connect() as conn:
        try:
            return pd.read_sql(text(query), conn, params=params)
        except Exception as e:
            st.error(f"Query Error: {e}")
            return pd.DataFrame()

def run_transaction(query, params=None):
    with engine.connect() as conn:
        try:
            conn.execute(text(query), params or {})
            conn.commit()
            return True
        except Exception as e:
            st.error(f"Transaction Failed: {e}")
            return False

# LOOKUP FUNCTIONS
def get_regions():
    df = run_query("SELECT region_id, region_name FROM Regions ORDER BY region_name")
    return dict(zip(df['region_name'], df['region_id']))

def get_staff():
    df = run_query("SELECT staff_id, name FROM Staff ORDER BY name")
    return dict(zip(df['name'], df['staff_id']))

def get_active_requests():
    df = run_query("SELECT request_id, request_type, status, priority FROM ServiceRequests ORDER BY request_date DESC")
    if df.empty: return {}
    options = {}
    for _, row in df.iterrows():
        label = f"#{row['request_id']} - {row['request_type']} ({row['status']})"
        options[label] = row['request_id']
    return options

# ==========================================
# 3. NAVIGATION
# ==========================================
st.sidebar.markdown("## Service Portal")
page = st.sidebar.radio("Navigation", ["Dashboard", "Case Management", "Staff Portal", "Data Reports"])

st.sidebar.markdown("---")
st.sidebar.caption("Global Filters")
date_range = st.sidebar.date_input("Date Range", [datetime.now() - timedelta(days=30), datetime.now()])

# ==========================================
# 4. DASHBOARD (Fixed SQL Errors)
# ==========================================
if page == "Dashboard":
    st.title("Executive Dashboard")
    st.markdown("Real-time overview of service demand and operational performance.")
    
    # Metrics Row
    m1, m2, m3, m4 = st.columns(4)
    
    total_vol = run_query("SELECT COUNT(*) FROM ServiceRequests").iloc[0,0]
    crit_open = run_query("SELECT COUNT(*) FROM ServiceRequests WHERE status != 'Closed' AND priority = 'Critical'").iloc[0,0]
    active_staff = run_query("SELECT COUNT(DISTINCT staff_id) FROM FollowUps WHERE followup_date >= CURRENT_DATE - 7").iloc[0,0]
    
    # Fixed Success Rate Query
    success_rate = run_query("""
        SELECT ROUND(100.0 * SUM(CASE WHEN completion_status = 'Completed' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) 
        FROM FollowUps
    """).iloc[0,0]
    success_rate = 0 if pd.isna(success_rate) else success_rate

    m1.metric("Total Requests", total_vol)
    m2.metric("Critical Open Cases", crit_open)
    m3.metric("Active Staff (7 Days)", active_staff)
    m4.metric("Resolution Rate", f"{success_rate}%")

    st.markdown("### Operational Analytics")
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.caption("Service Demand by Region")
        df_geo = run_query("""
            SELECT r.region_name, COUNT(s.request_id) as "Volume"
            FROM ServiceRequests s JOIN Regions r ON s.region_id = r.region_id 
            GROUP BY r.region_name ORDER BY "Volume" DESC
        """)
        st.bar_chart(df_geo.set_index("region_name"), color="#102a5c")

    with c2:
        st.caption("Priority Distribution")
        df_prio = run_query("""
            SELECT priority, COUNT(*) as "Count" 
            FROM ServiceRequests GROUP BY priority
        """)
        st.bar_chart(df_prio.set_index("priority"), color="#ff8200")

    st.markdown("### Resource Allocation")
    t1, t2 = st.tabs(["Staff Workload", "Timeline Analysis"])
    
    with t1:
        # FIXED SQL: Double quotes for alias
        df_load = run_query("""
            SELECT s.name, COUNT(f.followup_id) as "Cases Handled"
            FROM Staff s LEFT JOIN FollowUps f ON s.staff_id = f.staff_id
            GROUP BY s.name ORDER BY "Cases Handled" DESC
        """)
        st.bar_chart(df_load.set_index("name"))

    with t2:
        # FIXED SQL: Postgres Date Casting
        df_time = run_query("""
            SELECT request_date::date as "Date", COUNT(*) as "Count"
            FROM ServiceRequests 
            GROUP BY request_date::date
            ORDER BY "Date" ASC
        """)
        st.line_chart(df_time.set_index("Date"))

# ==========================================
# 5. CASE MANAGEMENT
# ==========================================
elif page == "Case Management":
    st.title("Case Management")
    
    tab_new, tab_manage = st.tabs(["New Request", "Manage Existing"])
    
    with tab_new:
        st.markdown("#### Intake Form")
        with st.form("intake_form"):
            c1, c2 = st.columns(2)
            with c1:
                new_type = st.selectbox("Request Type", ["Food Pantry", "Housing Support", "Utility Assistance", "Mental Health", "Childcare"])
                new_region_name = st.selectbox("Region", list(get_regions().keys()))
            with c2:
                new_prio = st.select_slider("Priority Level", ["Low", "Medium", "High", "Critical"])
                
            if st.form_submit_button("Create Request"):
                reg_id = get_regions()[new_region_name]
                success = run_transaction(
                    "INSERT INTO ServiceRequests (region_id, request_type, status, priority) VALUES (:r, :t, 'Open', :p)",
                    {"r": reg_id, "t": new_type, "p": new_prio}
                )
                if success:
                    st.success("Request created successfully.")
                    st.rerun()

    with tab_manage:
        st.markdown("#### Update or Delete Cases")
        request_map = get_active_requests()
        
        if not request_map:
            st.info("No active requests found.")
        else:
            selected_label = st.selectbox("Select Case", list(request_map.keys()))
            selected_id = request_map[selected_label]
            
            # Fetch Current Data
            curr = run_query(f"SELECT * FROM ServiceRequests WHERE request_id = {selected_id}").iloc[0]
            
            col_edit, col_del = st.columns([2, 1])
            with col_edit:
                st.write(f"**Current Status:** {curr['status']}")
                new_status = st.selectbox("Update Status", ["Open", "In Progress", "Closed"])
                if st.button("Update Status"):
                    run_transaction("UPDATE ServiceRequests SET status = :s WHERE request_id = :id", {"s": new_status, "id": selected_id})
                    st.success("Status Updated.")
                    st.rerun()
            
            with col_del:
                st.write("**Danger Zone**")
                if st.button("Delete Case"):
                    run_transaction("DELETE FROM FollowUps WHERE request_id = :id", {"id": selected_id})
                    run_transaction("DELETE FROM ServiceRequests WHERE request_id = :id", {"id": selected_id})
                    st.warning("Case Deleted.")
                    st.rerun()

    st.markdown("---")
    st.subheader("Case History")
    if request_map:
        # FIXED SQL: Double quotes for alias
        history_df = run_query("""
            SELECT f.followup_date, s.name as "Staff Member", f.notes, f.completion_status 
            FROM FollowUps f 
            JOIN Staff s ON f.staff_id = s.staff_id 
            WHERE f.request_id = :id ORDER BY f.followup_date DESC
        """, {"id": selected_id})
        
        st.dataframe(history_df, use_container_width=True)

# ==========================================
# 6. STAFF PORTAL
# ==========================================
elif page == "Staff Portal":
    st.title("Staff & Operations")
    
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.markdown("#### Log Activity")
        with st.form("log_work"):
            req_map = get_active_requests()
            if not req_map:
                st.warning("No cases available.")
                st.stop()
                
            req_label = st.selectbox("Case ID", list(req_map.keys()))
            staff_label = st.selectbox("Staff Member", list(get_staff().keys()))
            notes = st.text_area("Notes")
            outcome = st.selectbox("Outcome", ["Pending", "Completed", "Failed"])
            
            if st.form_submit_button("Log Entry"):
                rid = req_map[req_label]
                sid = get_staff()[staff_label]
                run_transaction("""
                    INSERT INTO FollowUps (request_id, staff_id, notes, completion_status, followup_date)
                    VALUES (:r, :s, :n, :c, CURRENT_DATE)
                """, {"r": rid, "s": sid, "n": notes, "c": outcome})
                st.success("Logged.")

    with c2:
        st.markdown("#### Staff Directory")
        st.dataframe(run_query("SELECT name, role, email FROM Staff"), use_container_width=True)
        
        with st.expander("Register New Staff"):
            with st.form("new_staff"):
                s_name = st.text_input("Name")
                s_role = st.selectbox("Role", ["Case Manager", "Volunteer", "Admin"])
                s_email = st.text_input("Email")
                if st.form_submit_button("Add User"):
                    run_transaction("INSERT INTO Staff (name, role, email) VALUES (:n, :r, :e)", 
                                   {"n": s_name, "r": s_role, "e": s_email})
                    st.success("User Added.")
                    st.rerun()

# ==========================================
# 7. REPORTS
# ==========================================
elif page == "Data Reports":
    st.title("Data Export Center")
    
    tab_req, tab_act = st.tabs(["Requests Data", "Activity Logs"])
    
    with tab_req:
        df_master = run_query("""
            SELECT s.request_id, r.region_name, s.request_type, s.status, s.priority, s.request_date 
            FROM ServiceRequests s 
            LEFT JOIN Regions r ON s.region_id = r.region_id
            ORDER BY s.request_id DESC
        """)
        st.dataframe(df_master, use_container_width=True)
        st.download_button("Download CSV", df_master.to_csv(index=False).encode('utf-8'), "requests.csv", "text/csv")
        
    with tab_act:
        df_audit = run_query("""
            SELECT f.followup_id, s.name as "Staff", r.request_type, f.notes, f.completion_status, f.followup_date
            FROM FollowUps f
            JOIN Staff s ON f.staff_id = s.staff_id
            JOIN ServiceRequests r ON f.request_id = r.request_id
            ORDER BY f.followup_date DESC
        """)
        st.dataframe(df_audit, use_container_width=True)
        st.download_button("Download CSV", df_audit.to_csv(index=False).encode('utf-8'), "activity_log.csv", "text/csv")
