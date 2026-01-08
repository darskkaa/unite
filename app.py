import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta

# ==========================================
# 1. CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="United Way Service Portal",
    page_icon="UW",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enterprise CSS
st.markdown("""
    <style>
    .stApp { background-color: #f4f6f9; }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    h1, h2, h3 { color: #102a5c; font-family: sans-serif; }
    .stButton>button {
        color: white; background-color: #ff8200; border: none; font-weight: 500;
    }
    .stButton>button:hover { background-color: #e67600; color: white; }
    .warning-card {
        padding: 15px; background-color: #fff3cd; color: #856404; 
        border: 1px solid #ffeeba; border-radius: 5px; margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. DATABASE & HELPERS
# ==========================================
try:
    db_url = st.secrets["db_url"]
    engine = create_engine(db_url)
except Exception:
    st.error("Database Connection Error. Check secrets.toml.")
    st.stop()

def run_query(query, params=None):
    with engine.connect() as conn:
        try:
            return pd.read_sql(text(query), conn, params=params)
        except Exception as e:
            return pd.DataFrame()

def run_transaction(query, params=None):
    with engine.connect() as conn:
        try:
            conn.execute(text(query), params or {})
            conn.commit()
            return True
        except Exception as e:
            st.error(f"Error: {e}")
            return False

# LOOKUPS
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
        options[f"#{row['request_id']} - {row['request_type']} ({row['status']})"] = row['request_id']
    return options

# ==========================================
# 3. NAVIGATION
# ==========================================
st.sidebar.markdown("## Service Portal")
page = st.sidebar.radio("Navigation", ["Dashboard", "Case Management", "Staff Portal", "Data Reports"])
st.sidebar.markdown("---")
st.sidebar.caption("Global Filters")
date_range = st.sidebar.date_input("Filter Data", [datetime.now() - timedelta(days=30), datetime.now()])

# ==========================================
# 4. DASHBOARD
# ==========================================
if page == "Dashboard":
    st.title("Executive Dashboard")
    
    # METRICS
    m1, m2, m3, m4 = st.columns(4)
    total_vol = run_query("SELECT COUNT(*) FROM ServiceRequests").iloc[0,0]
    crit_open = run_query("SELECT COUNT(*) FROM ServiceRequests WHERE status != 'Closed' AND priority = 'Critical'").iloc[0,0]
    
    # MISSING FEATURE: "Stale Cases" (No activity for 7+ days)
    stale_cases = run_query("""
        SELECT COUNT(*) FROM ServiceRequests 
        WHERE status != 'Closed' 
        AND request_id NOT IN (
            SELECT request_id FROM FollowUps WHERE followup_date >= CURRENT_DATE - 7
        )
    """).iloc[0,0]
    
    success_rate = run_query("""
        SELECT ROUND(100.0 * SUM(CASE WHEN completion_status = 'Completed' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) 
        FROM FollowUps
    """).iloc[0,0]

    m1.metric("Total Requests", total_vol)
    m2.metric("Critical Open Cases", crit_open)
    m3.metric("⚠️ Stale Cases (>7 Days)", stale_cases, delta_color="inverse")
    m4.metric("Resolution Rate", f"{0 if pd.isna(success_rate) else success_rate}%")

    # ANALYTICS
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
        st.caption("Resource Allocation (Workload)")
        df_load = run_query("""
            SELECT s.name, COUNT(f.followup_id) as "Cases Handled"
            FROM Staff s LEFT JOIN FollowUps f ON s.staff_id = f.staff_id
            GROUP BY s.name ORDER BY "Cases Handled" DESC
        """)
        st.bar_chart(df_load.set_index("name"), color="#ff8200")
        
        # MISSING FEATURE: Staff Overload Alert
        if not df_load.empty and df_load.iloc[0]["Cases Handled"] > 10:
            st.markdown(f"<div class='warning-card'>⚠️ <b>Resource Alert:</b> {df_load.iloc[0]['name']} has high caseload. Consider reassigning.</div>", unsafe_allow_html=True)

# ==========================================
# 5. CASE MANAGEMENT (Now with Detailed Notes)
# ==========================================
elif page == "Case Management":
    st.title("Case Management")
    tab_new, tab_manage = st.tabs(["New Request", "Manage Cases"])
    
    with tab_new:
        st.markdown("#### Detailed Intake Form")
        with st.form("intake_form"):
            c1, c2 = st.columns(2)
            with c1:
                new_type = st.selectbox("Request Type", ["Food Pantry", "Housing Support", "Utility Assistance", "Mental Health"])
                new_region_name = st.selectbox("Region", list(get_regions().keys()))
            with c2:
                new_prio = st.select_slider("Priority", ["Low", "Medium", "High", "Critical"])
            
            # MISSING FEATURE: Detailed Initial Notes
            new_desc = st.text_area("Detailed Description", placeholder="Enter specific client needs, family size, dietary restrictions, etc.", height=150)
            
            if st.form_submit_button("Create Request"):
                reg_id = get_regions()[new_region_name]
                success = run_transaction(
                    "INSERT INTO ServiceRequests (region_id, request_type, status, priority, description) VALUES (:r, :t, 'Open', :p, :d)",
                    {"r": reg_id, "t": new_type, "p": new_prio, "d": new_desc}
                )
                if success:
                    st.success("Request Created!"); st.rerun()

    with tab_manage:
        req_map = get_active_requests()
        if not req_map:
            st.info("No active cases.")
        else:
            sel_label = st.selectbox("Select Case", list(req_map.keys()))
            sel_id = req_map[sel_label]
            
            curr = run_query(f"SELECT * FROM ServiceRequests WHERE request_id = {sel_id}").iloc[0]
            
            # MISSING FEATURE: View Description
            with st.expander("📄 View Case Details & Description", expanded=True):
                st.markdown(f"**Details:** {curr.get('description', 'No description provided.')}")
                st.markdown(f"**Date:** {curr['request_date']} | **Status:** {curr['status']}")

            c_edit, c_del = st.columns([2, 1])
            with c_edit:
                new_stat = st.selectbox("Update Status", ["Open", "In Progress", "Closed"])
                if st.button("Update"):
                    run_transaction("UPDATE ServiceRequests SET status = :s WHERE request_id = :id", {"s": new_stat, "id": sel_id})
                    st.success("Updated!"); st.rerun()
            with c_del:
                if st.button("Delete Case", type="primary"):
                    run_transaction("DELETE FROM FollowUps WHERE request_id = :id", {"id": sel_id})
                    run_transaction("DELETE FROM ServiceRequests WHERE request_id = :id", {"id": sel_id})
                    st.warning("Deleted!"); st.rerun()

            st.markdown("### 📜 Activity Timeline")
            history = run_query("""
                SELECT f.followup_date, s.name as "Staff", f.notes, f.completion_status 
                FROM FollowUps f JOIN Staff s ON f.staff_id = s.staff_id 
                WHERE f.request_id = :id ORDER BY f.followup_date DESC
            """, {"id": sel_id})
            
            for _, row in history.iterrows():
                st.info(f"**{row['followup_date']} - {row['Staff']}** ({row['completion_status']})\n\n{row['notes']}")

# ==========================================
# 6. STAFF PORTAL (Improved Logging)
# ==========================================
elif page == "Staff Portal":
    st.title("Staff & Operations")
    
    with st.form("log_work"):
        st.subheader("📝 Log Activity")
        req_map = get_active_requests()
        if not req_map: st.stop()
        
        c1, c2 = st.columns(2)
        with c1:
            req_label = st.selectbox("Select Case", list(req_map.keys()))
            staff_label = st.selectbox("Staff Member", list(get_staff().keys()))
        with c2:
            # MISSING FEATURE: Back-dating
            log_date = st.date_input("Activity Date", datetime.now())
            outcome = st.selectbox("Outcome", ["Pending", "Completed", "Failed"])
            
        notes = st.text_area("Detailed Interaction Notes", height=150)
        
        if st.form_submit_button("Log Entry"):
            rid = req_map[req_label]
            sid = get_staff()[staff_label]
            run_transaction("""
                INSERT INTO FollowUps (request_id, staff_id, notes, completion_status, followup_date)
                VALUES (:r, :s, :n, :c, :d)
            """, {"r": rid, "s": sid, "n": notes, "c": outcome, "d": log_date})
            st.success("Logged!")

# ==========================================
# 7. REPORTS
# ==========================================
elif page == "Data Reports":
    st.title("Data Export Center")
    df_full = run_query("""
        SELECT s.request_id, r.region_name, s.request_type, s.description, s.status, s.priority, s.request_date 
        FROM ServiceRequests s LEFT JOIN Regions r ON s.region_id = r.region_id
        ORDER BY s.request_id DESC
    """)
    st.dataframe(df_full, use_container_width=True)
    st.download_button("Download CSV", df_full.to_csv(index=False).encode('utf-8'), "full_report.csv", "text/csv")
