import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta

# ==========================================
# CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="United Way Service Portal",
    page_icon="🤝",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "United Way Service Portal v2.0 (Mobile Optimized)"
    }
)

# ==========================================
# IOS & PWA CONFIGURATION
# ==========================================
st.markdown("""
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0, viewport-fit=cover">
""", unsafe_allow_html=True)

# ==========================================
# SOTA STYLING (Glassmorphism & Modern UI)
# ==========================================
st.markdown("""
    <style>
    /* GLOBAL VARIABLES */
    :root {
        --primary: #FF8200;
        --secondary: #102a5c;
        --bg-color: #f0f2f6;
        --card-bg: rgba(255, 255, 255, 0.9);
        --text-color: #102a5c;
    }
    
    /* TARGETED TEXT CONTRAST */
    h1, h2, h3, h4, h5, h6, .stMarkdown, .stMetricLabel {
        color: var(--text-color) !important;
    }
    
    .stMarkdown p {
        color: #333 !important;
    }
    
    /* APP BACKGROUND */
    .stApp {
        background: linear-gradient(135deg, #f0f2f6 0%, #e2e6ea 100%);
        color: var(--text-color);
    }

    /* CUSTOM METRIC CARDS */
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-left: 5px solid var(--secondary);
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.1);
    }
    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: var(--secondary);
        margin: 5px 0;
    }
    .metric-label {
        font-size: 14px;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-delta {
        font-size: 12px;
        font-weight: 600;
    }
    .delta-pos { color: #28a745; }
    .delta-neg { color: #dc3545; }

    /* WARNING CARDS */
    .warning-card {
        background: linear-gradient(to right, #fff3cd, #fff);
        border-left: 5px solid #ffc107;
        padding: 15px;
        border-radius: 8px;
        color: #856404;
        margin-bottom: 15px;
        display: flex;
        align-items: center;
        gap: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    /* HEADERS & TEXT */
    h1, h2, h3 {
        color: var(--secondary);
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    
    /* DATAFRAME STYLING */
    div[data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }

    /* BUTTONS */
    .stButton>button {
        background-color: var(--primary);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: background-color 0.2s;
    }
    .stButton>button:hover {
        background-color: #e67600;
        color: white;
        box-shadow: 0 2px 8px rgba(255, 130, 0, 0.4);
    }

    /* TABS */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: white;
        border-radius: 8px;
        padding: 10px 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stTabs [aria-selected="true"] {
        background-color: var(--secondary);
        color: white;
    }
    
    /* ==========================================
       MOBILE / SAFARI OPTIMIZATIONS
       ========================================== */
    @media (max-width: 768px) {
        /* Prevent Auto-Zoom on inputs by enforcing 16px */
        input, select, textarea {
            font-size: 16px !important;
            color: #000 !important;
            background-color: #fff !important;
        }
        
        /* Larger Touch Targets */
        .stButton>button {
            min-height: 48px;
            width: 100%;
            margin-bottom: 10px;
        }
        
        /* Sidebar & Layout Adjustments */
        section[data-testid="stSidebar"] {
            width: 100% !important;
        }
        
        /* Safe Area Insets (Notch/Dynamic Island) */
        .stApp {
            padding-top: env(safe-area-inset-top);
            padding-bottom: env(safe-area-inset-bottom);
            padding-left: env(safe-area-inset-left);
            padding-right: env(safe-area-inset-right);
        }
        
        /* Full Width Metrics on Mobile */
        div[data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }
        
        .metric-card {
            margin-bottom: 15px;
        }
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# DATABASE CONNECTION (CORE)
# ==========================================
try:
    db_url = st.secrets["db_url"]
    engine = create_engine(db_url)
except Exception:
    st.error("❌ Database Connection Error. Please verify `secrets.toml`.")
    st.stop()

def run_query(query, params=None):
    with engine.connect() as conn:
        try:
            return pd.read_sql(text(query), conn, params=params)
        except Exception:
            return pd.DataFrame()

def run_transaction(query, params=None):
    with engine.connect() as conn:
        try:
            conn.execute(text(query), params or {})
            conn.commit()
            return True
        except Exception as e:
            st.error(f"Transaction Error: {e}")
            return False

# ==========================================
# LOOKUPS & UTILS
# ==========================================
def get_regions():
    df = run_query("SELECT region_id, region_name FROM Regions ORDER BY region_name")
    if df.empty: return {}
    return dict(zip(df['region_name'], df['region_id']))

def get_staff():
    df = run_query("SELECT staff_id, name FROM Staff ORDER BY name")
    if df.empty: return {}
    return dict(zip(df['name'], df['staff_id']))

def get_active_requests():
    df = run_query("SELECT request_id, request_type, status, priority FROM ServiceRequests ORDER BY request_date DESC")
    if df.empty: return {}
    options = {}
    for _, row in df.iterrows():
        # Clean label for dropdown
        options[f"#{row['request_id']} | {row['request_type']} [{row['status']}]"] = row['request_id']
    return options

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.markdown(f"""
        <div style="text-align: center; padding: 10px; margin-bottom: 20px;">
            <h1 style="color: #102a5c; margin:0;">United Way</h1>
            <p style="color: #666; font-size: 0.9em;">Service Dashboard v2.0</p>
        </div>
    """, unsafe_allow_html=True)
    
    page = st.radio("Navigation", ["Dashboard", "Case Management", "Staff Portal", "Data Reports"], label_visibility="collapsed")
    
    st.markdown("---")
    st.markdown("### 📅 Global Filters")
    date_range = st.date_input("Filter Data", [datetime.now() - timedelta(days=30), datetime.now()])
    
    st.markdown("""
        <div style="position: fixed; bottom: 20px; font-size: 0.8em; color: #999;">
            Powered by Streamlit
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# PAGE: DASHBOARD
# ==========================================
if page == "Dashboard":
    st.markdown("## 📊 Executive Dashboard")
    
    # 1. METRICS ROW
    total_vol = run_query("SELECT COUNT(*) FROM ServiceRequests").iloc[0,0]
    crit_open = run_query("SELECT COUNT(*) FROM ServiceRequests WHERE status != 'Closed' AND priority = 'Critical'").iloc[0,0]
    
    # Logic: Stale = Not Closed AND No FollowUp in last 7 days
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

    cols = st.columns(4)
    metrics = [
        ("Total Requests", total_vol, "#102a5c"),
        ("Critical Open", crit_open, "#dc3545"),
        ("Stale Cases (>7d)", stale_cases, "#ffc107" if stale_cases > 0 else "#28a745"),
        ("Resolution Rate", f"{0 if pd.isna(success_rate) else success_rate}%", "#28a745")
    ]

    for col, (label, val, color) in zip(cols, metrics):
        col.markdown(f"""
            <div class="metric-card" style="border-left-color: {color};">
                <div class="metric-label">{label}</div>
                <div class="metric-value" style="color: {color};">{val}</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # 2. ANALYTICS
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("### 🗺️ Service Demand by Region")
        df_geo = run_query("""
            SELECT r.region_name, COUNT(s.request_id) as "Volume"
            FROM ServiceRequests s JOIN Regions r ON s.region_id = r.region_id 
            GROUP BY r.region_name ORDER BY "Volume" ASC
        """)
        if not df_geo.empty:
            fig = px.bar(df_geo, x="Volume", y="region_name", orientation='h', 
                         color="Volume", color_continuous_scale="Blues", text_auto=True)
            fig.update_layout(xaxis_title=None, yaxis_title=None, height=350, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available.")

    with c2:
        st.markdown("### 👥 Resource Workload")
        df_load = run_query("""
            SELECT s.name, COUNT(f.followup_id) as "Cases Handled"
            FROM Staff s LEFT JOIN FollowUps f ON s.staff_id = f.staff_id
            GROUP BY s.name ORDER BY "Cases Handled" DESC
        """)
        
        # LOGIC: Check for Overload (>10 cases)
        overloaded = df_load[df_load["Cases Handled"] > 10]['name'].tolist()
        if overloaded:
            st.markdown(f"""
                <div class="warning-card">
                    ⚠️ <b>Resource Alert:</b> High utilization for: {", ".join(overloaded)}
                </div>
            """, unsafe_allow_html=True)

        if not df_load.empty:
            fig2 = px.bar(df_load, x="name", y="Cases Handled", 
                          color="Cases Handled", color_continuous_scale="Oranges", text_auto=True)
            fig2.update_layout(xaxis_title=None, yaxis_title=None, height=350)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No data available.")

# ==========================================
# PAGE: CASE MANAGEMENT
# ==========================================
elif page == "Case Management":
    st.markdown("## 📁 Case Management")
    tab_new, tab_manage = st.tabs(["➕ New Request", "🛠️ Manage Active Cases"])

    with tab_new:
        with st.container():
            st.markdown("#### Patient Intake Form")
            st.markdown("<p style='font-size: 0.9em; margin-bottom: 20px;'>Fill out all details below to generate a new service request.</p>", unsafe_allow_html=True)
            
            with st.form("intake_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    new_type = st.selectbox("Request Type", ["Food Pantry", "Housing Support", "Utility Assistance", "Mental Health", "Other"])
                    # Use keys for logic
                    regions_map = get_regions()
                    new_region_name = st.selectbox("Region", list(regions_map.keys()) if regions_map else [])
                with c2:
                    new_prio = st.select_slider("Priority Level", ["Low", "Medium", "High", "Critical"])

                new_desc = st.text_area("Detailed Situation Description", 
                    placeholder="Enter specific client needs, family size, immediate risks...", height=120)

                submitted = st.form_submit_button("Create Service Request", type="primary")
                
                if submitted:
                    if not new_region_name:
                        st.error("Please configure Regions first.")
                    else:
                        reg_id = regions_map[new_region_name]
                        success = run_transaction(
                            "INSERT INTO ServiceRequests (region_id, request_type, status, priority, description) VALUES (:r, :t, 'Open', :p, :d)",
                            {"r": reg_id, "t": new_type, "p": new_prio, "d": new_desc}
                        )
                        if success:
                            st.balloons()
                            st.success("✅ Request Created Successfully!")
                            st.rerun()

    with tab_manage:
        req_map = get_active_requests()
        if not req_map:
            st.info("🎉 No active cases found!")
        else:
            c_sel, c_acts = st.columns([1, 2])
            with c_sel:
                st.markdown("#### Select Case")
                sel_label = st.selectbox("Search Active Cases", list(req_map.keys()))
                sel_id = req_map[sel_label]
                
                # Fetch details
                curr = run_query(f"SELECT * FROM ServiceRequests WHERE request_id = {sel_id}").iloc[0]
                
                # Card View
                st.markdown(f"""
                <div style="background:white; padding:20px; border-radius:10px; border:1px solid #ddd; margin-top:10px;">
                    <h3 style="margin-top:0;">Case #{sel_id}</h3>
                    <p><b>Type:</b> {curr['request_type']}</p>
                    <p><b>Date:</b> {curr['request_date']}</p>
                    <p><b>Priority:</b> <span style="background:{'#FFcccc' if curr['priority']=='Critical' else '#eee'}; padding:2px 8px; border-radius:4px;">{curr['priority']}</span></p>
                    <hr>
                    <p style="font-style:italic;">"{curr.get('description') or 'No description provided.'}"</p>
                </div>
                """, unsafe_allow_html=True)

            with c_acts:
                st.markdown("#### Actions & History")
                
                # UPDATE STATUS
                c1, c2 = st.columns([2, 1])
                with c1:
                    new_stat = st.selectbox("Update Status", ["Open", "In Progress", "Closed"], key="stat_upd")
                with c2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("Update Status"):
                        run_transaction("UPDATE ServiceRequests SET status = :s WHERE request_id = :id", {"s": new_stat, "id": sel_id})
                        st.success("Status Updated!")
                        st.rerun()
                
                # DELETE
                with st.expander("🗑️ Danger Zone"):
                    st.markdown("Deleting a case will permanently remove it and all associated follow-ups.")
                    if st.button("Delete Case Permanently", type="primary"):
                        # SAFE DELETE LOGIC
                        run_transaction("DELETE FROM FollowUps WHERE request_id = :id", {"id": sel_id})
                        run_transaction("DELETE FROM ServiceRequests WHERE request_id = :id", {"id": sel_id})
                        st.warning("Case Deleted.")
                        st.rerun()

                # HISTORY TIMELINE
                st.markdown("#### 📜 Activity Log")
                history = run_query("""
                    SELECT f.followup_date, s.name as "Staff", f.notes, f.completion_status 
                    FROM FollowUps f JOIN Staff s ON f.staff_id = s.staff_id 
                    WHERE f.request_id = :id ORDER BY f.followup_date DESC
                """, {"id": sel_id})
                
                if history.empty:
                    st.caption("No activity logged yet.")
                else:
                    for _, row in history.iterrows():
                        icon = "✅" if row['completion_status'] == 'Completed' else "⚠️" if row['completion_status'] == 'Failed' else "⏳"
                        st.markdown(f"""
                        <div style="border-left: 3px solid #ddd; padding-left: 15px; margin-bottom: 20px;">
                            <div style="font-weight:bold; color:#102a5c;">{icon} {row['completion_status']} - {row['followup_date']}</div>
                            <div style="font-size:0.9em; color:#666;">by {row['Staff']}</div>
                            <div style="margin-top:5px;">{row['notes']}</div>
                        </div>
                        """, unsafe_allow_html=True)

# ==========================================
# PAGE: STAFF PORTAL
# ==========================================
elif page == "Staff Portal":
    st.markdown("## 👷 Staff & Operations Portal")
    
    st.markdown("<div class='metric-card'>📝 <b>Log Daily Activity</b><br>Record your interactions with clients here in real-time.</div><br>", unsafe_allow_html=True)

    with st.form("log_work"):
        req_map = get_active_requests()
        staff_map = get_staff()
        
        if not req_map or not staff_map:
            st.warning("System not fully configured. Needs Active Requests and Staff Members.")
            st.stop()

        c1, c2 = st.columns(2)
        with c1:
            req_label = st.selectbox("Select Case", list(req_map.keys()))
            staff_label = st.selectbox("Staff Member", list(staff_map.keys()))
        with c2:
            log_date = st.date_input("Activity Date", datetime.now())
            outcome = st.selectbox("Outcome", ["Pending", "Completed", "Failed"])

        notes = st.text_area("Detailed Interaction Notes", height=150, placeholder="Client was contacted via phone...")

        if st.form_submit_button("Submit Activity Log", type="primary"):
            rid = req_map[req_label]
            sid = staff_map[staff_label]
            
            run_transaction("""
                INSERT INTO FollowUps (request_id, staff_id, notes, completion_status, followup_date)
                VALUES (:r, :s, :n, :c, :d)
            """, {"r": rid, "s": sid, "n": notes, "c": outcome, "d": log_date})
            
            st.success("Activity Logged Successfully!")

# ==========================================
# PAGE: REPORTS
# ==========================================
elif page == "Data Reports":
    st.markdown("## 📥 Data Export Center")
    
    df_full = run_query("""
        SELECT s.request_id, r.region_name, s.request_type, s.description, s.status, s.priority, s.request_date 
        FROM ServiceRequests s LEFT JOIN Regions r ON s.region_id = r.region_id
        ORDER BY s.request_id DESC
    """)
    
    st.dataframe(
        df_full, 
        use_container_width=True,
        column_config={
            "status": st.column_config.SelectboxColumn(
                "Status",
                help="Current case status",
                width="medium",
                options=["Open", "In Progress", "Closed"],
            ),
            "priority": st.column_config.TextColumn("Priority", width="small"),
            "request_date": st.column_config.DatetimeColumn("Date", format="D MMM YYYY"),
        }
    )
    
    if not df_full.empty:
        st.download_button(
            "📥 Download Full Report (CSV)", 
            df_full.to_csv(index=False).encode('utf-8'), 
            f"united_way_report_{datetime.now().date()}.csv", 
            "text/csv"
        )
