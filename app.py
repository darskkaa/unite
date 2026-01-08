import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta

# ==========================================
# 1. CONFIGURATION & SETUP
# ==========================================
st.set_page_config(
    page_title="United Way Service Portal",
    page_icon="💙",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS to make it look like a real SaaS product
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    h1, h2, h3 {
        color: #0f2b5a; /* United Way Dark Blue */
    }
    .stButton>button {
        color: white;
        background-color: #ff8200; /* United Way Orange */
        border: none;
    }
    .stButton>button:hover {
        background-color: #e67600;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        color: #155724;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. DATABASE CONNECTION & HELPER FUNCTIONS
# ==========================================
try:
    # Secure connection via secrets
    db_url = st.secrets["db_url"]
    engine = create_engine(db_url)
except Exception as e:
    st.error(f"🚨 CRITICAL ERROR: Could not connect to Database. Check secrets.toml. \n\nDetails: {e}")
    st.stop()

def run_query(query, params=None):
    """Executes a SQL query and returns a Pandas DataFrame."""
    with engine.connect() as conn:
        try:
            return pd.read_sql(text(query), conn, params=params)
        except Exception as e:
            st.error(f"Query Error: {e}")
            return pd.DataFrame()

def run_transaction(query, params=None):
    """Executes an INSERT/UPDATE/DELETE statement."""
    with engine.connect() as conn:
        try:
            conn.execute(text(query), params or {})
            conn.commit()
            return True
        except Exception as e:
            st.error(f"Transaction Failed: {e}")
            return False

# --- CACHED LOOKUP FUNCTIONS (For Dropdowns) ---
def get_regions():
    df = run_query("SELECT region_id, region_name FROM Regions ORDER BY region_name")
    return dict(zip(df['region_name'], df['region_id']))

def get_staff():
    df = run_query("SELECT staff_id, name FROM Staff ORDER BY name")
    return dict(zip(df['name'], df['staff_id']))

def get_active_requests():
    """Returns a dictionary formatted for dropdowns: 'ID: Type (Status)'"""
    df = run_query("SELECT request_id, request_type, status, priority FROM ServiceRequests ORDER BY request_date DESC")
    if df.empty: return {}
    options = {}
    for _, row in df.iterrows():
        label = f"#{row['request_id']} | {row['request_type']} ({row['status']}) - {row['priority']}"
        options[label] = row['request_id']
    return options

# ==========================================
# 3. SIDEBAR NAVIGATION
# ==========================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/en/thumb/0/06/United_Way_Main_Logo.svg/1200px-United_Way_Main_Logo.svg.png", width=200)
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["📊 Executive Dashboard", "📂 Case Management", "👥 Staff Portal", "📥 Reports & Data"])

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔍 Global Filters")
# Global date filter that could apply to charts
date_range = st.sidebar.date_input("Filter Analytics By Date", [datetime.now() - timedelta(days=30), datetime.now()])

# ==========================================
# 4. PAGE: EXECUTIVE DASHBOARD
# ==========================================
if page == "📊 Executive Dashboard":
    st.title("📊 Executive Dashboard")
    st.markdown("Overview of service demand, staff performance, and community impact.")
    
    # --- Top Level Metrics ---
    m1, m2, m3, m4 = st.columns(4)
    
    # 1. Total Volume
    total_vol = run_query("SELECT COUNT(*) FROM ServiceRequests").iloc[0,0]
    m1.metric("Total Requests", total_vol, delta_color="normal")
    
    # 2. Critical Open Cases
    crit_open = run_query("SELECT COUNT(*) FROM ServiceRequests WHERE status != 'Closed' AND priority = 'Critical'").iloc[0,0]
    m2.metric("Critical Open Cases", crit_open, delta="Urgent", delta_color="inverse")
    
    # 3. Staff Utilization
    active_staff = run_query("SELECT COUNT(DISTINCT staff_id) FROM FollowUps WHERE followup_date >= CURRENT_DATE - 7").iloc[0,0]
    m3.metric("Staff Active (7 Days)", active_staff)
    
    # 4. Success Rate (Requirement: Patterns in follow-up)
    success_rate = run_query("""
        SELECT ROUND(100.0 * SUM(CASE WHEN completion_status = 'Completed' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) 
        FROM FollowUps
    """).iloc[0,0]
    success_rate = 0 if pd.isna(success_rate) else success_rate
    m4.metric("Resolution Rate", f"{success_rate}%")

    st.markdown("---")

    # --- Row 1: Charts ---
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("📍 Service Demand by Region")
        # Requirement: Service demand by region
        df_geo = run_query("""
            SELECT r.region_name, COUNT(s.request_id) as Volume 
            FROM ServiceRequests s JOIN Regions r ON s.region_id = r.region_id 
            GROUP BY r.region_name ORDER BY Volume DESC
        """)
        st.bar_chart(df_geo.set_index("region_name"), color="#0f2b5a") # United Way Blue

    with c2:
        st.subheader("⚠️ Request Priority Distribution")
        df_prio = run_query("SELECT priority, COUNT(*) as Count FROM ServiceRequests GROUP BY priority")
        st.bar_chart(df_prio.set_index("priority"), color="#ff8200") # United Way Orange

    # --- Row 2: Advanced Analytics ---
    st.subheader("📈 Resource Allocation & Trends")
    t1, t2 = st.tabs(["Staff Workload", "Timeline Analysis"])
    
    with t1:
        # Requirement: Resource allocation optimization
        st.markdown("**Current Workload per Staff Member**")
        df_load = run_query("""
            SELECT s.name, COUNT(f.followup_id) as 'Cases Handled'
            FROM Staff s LEFT JOIN FollowUps f ON s.staff_id = f.staff_id
            GROUP BY s.name ORDER BY 'Cases Handled' DESC
        """)
        st.bar_chart(df_load.set_index("name"))
        st.caption("Use this chart to identify overworked staff members.")

    with t2:
        st.markdown("**Incoming Requests (Last 30 Days)**")
        df_time = run_query("""
            SELECT DATE(request_date) as Date, COUNT(*) as Count 
            FROM ServiceRequests 
            GROUP BY DATE(request_date) 
            ORDER BY Date ASC
        """)
        st.line_chart(df_time.set_index("Date"))

# ==========================================
# 5. PAGE: CASE MANAGEMENT (CRUD CENTER)
# ==========================================
elif page == "📂 Case Management":
    st.title("📂 Case Management Portal")
    
    tab_new, tab_manage = st.tabs(["➕ New Request", "🛠️ Manage Existing Cases"])
    
    # --- TAB 1: CREATE ---
    with tab_new:
        st.markdown("### Intake Form")
        with st.form("intake_form"):
            col_a, col_b = st.columns(2)
            with col_a:
                new_type = st.selectbox("Request Type", ["Food Pantry", "Housing Support", "Utility Assistance", "Mental Health", "Childcare"])
                new_region_name = st.selectbox("Region", list(get_regions().keys()))
            with col_b:
                new_prio = st.select_slider("Priority Level", ["Low", "Medium", "High", "Critical"])
                
            submitted = st.form_submit_button("Create Service Request")
            
            if submitted:
                reg_id = get_regions()[new_region_name]
                success = run_transaction(
                    "INSERT INTO ServiceRequests (region_id, request_type, status, priority) VALUES (:r, :t, 'Open', :p)",
                    {"r": reg_id, "t": new_type, "p": new_prio}
                )
                if success:
                    st.success(f"✅ Request Created Successfully for {new_region_name}!")
                    st.rerun()

    # --- TAB 2: UPDATE / DELETE ---
    with tab_manage:
        st.markdown("### Update or Delete Cases")
        
        request_map = get_active_requests()
        if not request_map:
            st.warning("No active requests found.")
        else:
            selected_label = st.selectbox("Select a Case to Manage", list(request_map.keys()))
            selected_id = request_map[selected_label]
            
            # Fetch current details
            current_data = run_query(f"SELECT * FROM ServiceRequests WHERE request_id = {selected_id}").iloc[0]
            
            col_edit, col_del = st.columns([2, 1])
            
            with col_edit:
                st.info(f"**Current Status:** {current_data['status']} | **Date:** {current_data['request_date']}")
                new_status = st.selectbox("Update Status", ["Open", "In Progress", "Closed"], key="status_update")
                
                if st.button("💾 Save Status Change"):
                    run_transaction("UPDATE ServiceRequests SET status = :s WHERE request_id = :id", {"s": new_status, "id": selected_id})
                    st.success("Status Updated!")
                    st.rerun()

            with col_del:
                st.error("⚠️ Danger Zone")
                st.markdown("Deleting a case will remove **ALL** associated follow-up history.")
                if st.button("🗑️ DELETE CASE"):
                    # Transactional Delete: Children first, then Parent
                    run_transaction("DELETE FROM FollowUps WHERE request_id = :id", {"id": selected_id})
                    run_transaction("DELETE FROM ServiceRequests WHERE request_id = :id", {"id": selected_id})
                    st.toast("Case deleted successfully.", icon="🗑️")
                    st.rerun()

    # --- CASE HISTORY VIEW (Requirement: Track completion) ---
    st.markdown("---")
    st.subheader("📜 Selected Case History")
    if request_map:
        history_df = run_query("""
            SELECT f.followup_date, s.name as 'Staff Member', f.notes, f.completion_status 
            FROM FollowUps f 
            JOIN Staff s ON f.staff_id = s.staff_id 
            WHERE f.request_id = :id ORDER BY f.followup_date DESC
        """, {"id": selected_id})
        
        if history_df.empty:
            st.caption("No follow-up history found for this case.")
        else:
            st.dataframe(history_df, use_container_width=True)

# ==========================================
# 6. PAGE: STAFF PORTAL
# ==========================================
elif page == "👥 Staff Portal":
    st.title("👥 Staff & Operations Portal")
    
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.markdown("### 📝 Log Follow-Up")
        st.caption("Record actions taken on a specific case.")
        
        with st.form("log_work"):
            req_map = get_active_requests()
            if not req_map:
                st.warning("No cases available.")
                st.stop()
                
            req_label = st.selectbox("Select Case", list(req_map.keys()))
            staff_label = st.selectbox("Staff Member", list(get_staff().keys()))
            
            notes = st.text_area("Interaction Notes", placeholder="e.g. Called client, arranged food delivery...")
            outcome = st.selectbox("Outcome", ["Pending", "Completed", "Failed"])
            
            if st.form_submit_button("Log Activity"):
                rid = req_map[req_label]
                sid = get_staff()[staff_label]
                
                success = run_transaction("""
                    INSERT INTO FollowUps (request_id, staff_id, notes, completion_status, followup_date)
                    VALUES (:r, :s, :n, :c, CURRENT_DATE)
                """, {"r": rid, "s": sid, "n": notes, "c": outcome})
                
                if success:
                    st.success("Activity Logged!")

    with c2:
        st.markdown("### 🧑‍💼 Staff Directory")
        st.caption("Manage your team.")
        
        staff_df = run_query("SELECT staff_id, name, role, email FROM Staff")
        st.dataframe(staff_df, use_container_width=True, hide_index=True)
        
        with st.expander("➕ Hire New Staff Member"):
            with st.form("new_staff"):
                s_name = st.text_input("Full Name")
                s_role = st.selectbox("Role", ["Case Manager", "Volunteer", "Admin", "Intern"])
                s_email = st.text_input("Email")
                if st.form_submit_button("Add Staff"):
                    run_transaction(
                        "INSERT INTO Staff (name, role, email) VALUES (:n, :r, :e)",
                        {"n": s_name, "r": s_role, "e": s_email}
                    )
                    st.success(f"Welcome to the team, {s_name}!")
                    st.rerun()

# ==========================================
# 7. PAGE: REPORTS & DATA
# ==========================================
elif page == "📥 Reports & Data":
    st.title("📥 Data Export Center")
    st.markdown("Generate summary reports for stakeholders.")
    
    # Requirement: Generate summary reports
    
    tab_req, tab_act = st.tabs(["Full Request Data", "Activity Logs"])
    
    with tab_req:
        st.subheader("Master Service Request Log")
        # Join with Region for readability
        df_master = run_query("""
            SELECT s.request_id, r.region_name, s.request_type, s.status, s.priority, s.request_date 
            FROM ServiceRequests s 
            LEFT JOIN Regions r ON s.region_id = r.region_id
            ORDER BY s.request_id DESC
        """)
        st.dataframe(df_master, use_container_width=True)
        
        # Download Button
        csv_data = df_master.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📄 Download Full Report (CSV)",
            data=csv_data,
            file_name=f"united_way_requests_{datetime.now().strftime('%Y-%m-%d')}.csv",
            mime="text/csv"
        )
        
    with tab_act:
        st.subheader("Staff Activity Audit")
        df_audit = run_query("""
            SELECT f.followup_id, s.name as Staff, r.request_type, f.notes, f.completion_status, f.followup_date
            FROM FollowUps f
            JOIN Staff s ON f.staff_id = s.staff_id
            JOIN ServiceRequests r ON f.request_id = r.request_id
            ORDER BY f.followup_date DESC
        """)
        st.dataframe(df_audit, use_container_width=True)
        
        csv_audit = df_audit.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📄 Download Activity Log (CSV)",
            data=csv_audit,
            file_name="staff_activity_audit.csv",
            mime="text/csv"
        )
