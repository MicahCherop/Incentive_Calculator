import streamlit as st
import pandas as pd
import numpy as np
import os
import urllib.parse
from sqlalchemy import create_engine, text
import pymysql

# 1. Page Setup
st.set_page_config(
    page_title="UPIA Incentive System", 
    page_icon="🏢", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 🔓 UI CUSTOMIZATION ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stAppDeployButton {display:none;}
    [data-testid="stHeader"] { background: rgba(0,0,0,0); } 
    [data-testid="stSidebar"] { min-width: 300px; max-width: 300px; }
    .block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 🗄️ DATABASE MANAGEMENT (MySQL) ---
def get_db_engine():
    """Creates an SQLAlchemy engine using Streamlit Secrets with URL encoding."""
    try:
        # Check if secrets exist
        if "mysql" not in st.secrets:
            st.error("🚨 Missing [mysql] section in Streamlit Secrets! Please configure your secrets.")
            st.stop()

        db_user = st.secrets["mysql"]["user"]
        raw_pass = st.secrets["mysql"]["password"]
        db_host = st.secrets["mysql"]["host"]
        db_port = st.secrets["mysql"]["port"]
        db_name = st.secrets["mysql"]["database"]
        
        # ⚠️ NEW: Prevent the app from crashing if 127.0.0.1 is used on the cloud
        if db_host in ["127.0.0.1", "localhost"]:
            st.error(
                "🚨 **Database Connection Blocked:** \n"
                "Your Secrets are currently trying to connect to `127.0.0.1` (localhost). "
                "Because this app is hosted on Streamlit Cloud, it cannot see your local computer's database. \n\n"
                "**Fix:** Please update your Streamlit Cloud Secrets with the **Public IP** or **External Hostname** of your database."
            )
            st.stop()
            
        # Safely encode the password to handle special characters like '@'
        safe_pass = urllib.parse.quote_plus(raw_pass)
        
        # Connection string for MySQL
        connection_string = f"mysql+pymysql://{db_user}:{safe_pass}@{db_host}:{db_port}/{db_name}"
        return create_engine(connection_string)
    except Exception as e:
        st.error(f"MySQL configuration error: {e}")
        st.stop()

def load_targets_from_db():
    """Reads the current targets from the MySQL database."""
    engine = get_db_engine()
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SHOW TABLES LIKE 'monthly_targets'"))
            if result.fetchone() is None:
                return pd.DataFrame()
                
        df = pd.read_sql_table("monthly_targets", con=engine)
        return standardize_merge_keys(df)
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return pd.DataFrame()

# --- 🛡️ ROBUST STRING CLEANER ---
def standardize_merge_keys(df):
    """Cleans merge keys to prevent mismatches due to typos or formatting."""
    for col in ['Branch', 'Subsector', 'Sector', 'Role']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.title()
            df[col] = df[col].str.replace(r'\s+', ' ', regex=True) 
            df[col] = df[col].replace({'Nan': np.nan, 'None': np.nan})
            
    if 'Pair_ID' in df.columns:
        df['Pair_ID'] = df['Pair_ID'].astype(str).str.strip().str.upper()
        df['Pair_ID'] = df['Pair_ID'].str.replace(r'\s+', ' ', regex=True)
        df['Pair_ID'] = df['Pair_ID'].str.replace(r'\.0$', '', regex=True) 
        df['Pair_ID'] = df['Pair_ID'].replace({'NAN': np.nan, 'NONE': np.nan})
        
    return df

# 2. Optimized Helper Functions
@st.cache_data
def process_performance_data(file):
    df = pd.read_csv(file)
    df.columns = [str(c).strip().replace(' ', '_') for c in df.columns]
    df = df.loc[:, ~df.columns.str.contains('^Unnamed', case=False, na=False)]
    
    num_cols = ['New_Customers', 'Unique_Customers', 'Active_Customers', 'Dormant_Customers', 
                'Amount_Collected', 'DD_Plus_7_Pct', 'OTC_Pct', 'Overall_Collection_Pct', 
                'Disb_Actual']
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).replace(r'[^-0-9.]', '', regex=True), 
                errors='coerce'
            ).fillna(0)
            
    return standardize_merge_keys(df)

@st.cache_data
def load_staff_directory(file):
    df = pd.read_csv(file, dtype={'Phone_Number': str, 'Pair_ID': str})
    df.columns = [str(c).strip().replace(' ', '_') for c in df.columns]
    df = df.loc[:, ~df.columns.str.contains('^Unnamed', case=False, na=False)]
    return standardize_merge_keys(df)


# --- 🏢 MAIN INTERFACE ---
st.title("UPIA Incentive System 🏢")

tab_calc, tab_db = st.tabs(["📊 Calculator Engine", "🗄️ Daily Target Database"])

LEVEL_CONFIG = {
    "Pairs (LO & CO)": {"group_key": ["Branch", "Pair_ID"], "unit_name": "Pair_ID", "match_key": "Pair_ID"},
    "Branch Managers": {"group_key": "Branch", "unit_name": "Pair_ID", "match_key": "Branch"},
    "Assistant Sector Managers": {"group_key": "Subsector", "unit_name": "Branch", "match_key": "Subsector"},
    "Sector Managers": {"group_key": "Sector", "unit_name": "Branch", "match_key": "Sector"}
}

# --- SIDEBAR CONFIGURATION ---
st.sidebar.title("Configuration")
eval_level = st.sidebar.selectbox("1. Select Evaluation Level", list(LEVEL_CONFIG.keys()))
campaign_name = st.sidebar.selectbox("2. Select Campaign", ["New Customers", "Unique Customers", "Active Customers", "Dormant Customers", "Collections", "Disbursements"])

st.sidebar.divider() 

scale_threshold = 1
if eval_level == "Assistant Sector Managers": 
    scale_threshold = st.sidebar.number_input("Standard ASM Branch Count", value=4)
elif eval_level == "Sector Managers": 
    scale_threshold = st.sidebar.number_input("Standard Sector Branch Count", value=25)

st.sidebar.write("### 💵 Payout Settings")
base_bonus = st.sidebar.number_input("Base Bonus Amount", value=3000.0, step=500.0)

bonus_step_count = 1.0
bonus_step_amount = 0.0

if "Customers" in campaign_name:
    col1, col2 = st.sidebar.columns(2)
    with col1: bonus_step_count = st.number_input("For every (Qty)", value=2.0, min_value=1.0)
    with col2: bonus_step_amount = st.number_input("Pay Extra (KES)", value=200.0)
elif campaign_name == "Disbursements":
    col1, col2 = st.sidebar.columns(2)
    with col1: bonus_step_count = st.number_input("For every (X%)", value=1.0, min_value=0.1)
    with col2: bonus_step_amount = st.number_input("Pay Extra (KES)", value=200.0)

targets = {}
active_filters = []

if "Customers" in campaign_name:
    key = campaign_name.replace(" ", "_")
    targets[key] = st.sidebar.number_input(f"Base Min {campaign_name} Required", value=6.0)
    active_filters.append(key)
elif campaign_name == "Collections":
    if st.sidebar.checkbox("Filter by Amount Collected", value=True):
        targets["Amount_Collected"] = st.sidebar.number_input("Min Amount", value=50000.0)
        active_filters.append("Amount_Collected")
    if st.sidebar.checkbox("Filter by OTC %", value=True):
        targets["OTC_Pct"] = st.sidebar.number_input("Min OTC (%)", value=91.0)
        active_filters.append("OTC_Pct")
    if st.sidebar.checkbox("Filter by DD+7 %", value=True):
        targets["DD_Plus_7_Pct"] = st.sidebar.number_input("Min DD+7 (%)", value=94.0)
        active_filters.append("DD_Plus_7_Pct")
elif campaign_name == "Disbursements":
    targets["disb_threshold"] = st.sidebar.number_input("Qualification Threshold (%)", value=100.0)
    active_filters.append("disb_threshold")

# ==========================================
# TAB 2: DATABASE MANAGEMENT (MySQL)
# ==========================================
# ==========================================
# TAB 2: DATABASE MANAGEMENT (MySQL)
# ==========================================
with tab_db:
    st.header("🗄️ Manage Monthly Targets")
    st.write("Upload a new Target CSV to overwrite the current **MySQL** database.")
    
    new_db_file = st.file_uploader("Upload New Master Targets CSV", type=['csv'])
    
    if new_db_file:
        raw_db_df = pd.read_csv(new_db_file)
        raw_db_df.columns = [str(c).strip().replace(' ', '_') for c in raw_db_df.columns]
        raw_db_df = raw_db_df.loc[:, ~raw_db_df.columns.str.contains('^Unnamed', case=False, na=False)]
        
        # Clean numeric target values
        for col in raw_db_df.columns:
            if col not in ['Pair_ID', 'Branch', 'Subsector', 'Sector']:
                raw_db_df[col] = pd.to_numeric(raw_db_df[col].astype(str).replace(r'[^-0-9.]', '', regex=True), errors='coerce').fillna(0)
        
        clean_db_df = standardize_merge_keys(raw_db_df)

        # 🛠️ CREATE A UNIQUE INDEX COLUMN
        # This combines Branch and Pair_ID so 'Nairobi_Pair 1' is different from 'Mombasa_Pair 1'
        clean_db_df['Unique_ID'] = clean_db_df['Branch'].astype(str) + "_" + clean_db_df['Pair_ID'].astype(str)
        
        # Now drop duplicates based on the new Unique_ID
        clean_db_df = clean_db_df.drop_duplicates(subset=['Unique_ID'])
        
        st.write(f"✅ Processing {len(clean_db_df)} unique Branch-Pair records.")

        try:
            engine = get_db_engine()
            
            # Set our new Unique_ID as the index for the database
            upload_df = clean_db_df.set_index('Unique_ID')
            
            from sqlalchemy import String
            dtype_map = {'Unique_ID': String(200)}

            # Write to SQL
            upload_df.to_sql(
                'monthly_targets', 
                engine, 
                if_exists='replace', 
                index=True, 
                dtype=dtype_map
            )
            
            # Explicitly set the Primary Key for Aiven
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE monthly_targets ADD PRIMARY KEY (Unique_ID);"))
                conn.commit()
                
            st.success("✅ MySQL Database updated! All pairs across all branches are now saved.")
            
        except Exception as e:
            st.error(f"Failed to update MySQL: {e}")

    st.divider()
    
    st.subheader("Current Database View")
    current_db = load_targets_from_db()
    if not current_db.empty:
        st.dataframe(current_db, use_container_width=True)
    else:
        st.warning("Database is empty. Please upload targets.")

# ==========================================
# TAB 1: CALCULATOR ENGINE
# ==========================================
with tab_calc:
    c1, c2 = st.columns(2)
    with c1: perf_file = st.file_uploader("1. Upload Actuals CSV", type=['csv'])
    with c2: staff_file = st.file_uploader("2. Upload Staff Directory CSV", type=['csv'])

    if perf_file:
        target_df = load_targets_from_db()
        if target_df.empty:
            st.error("🚨 Target Database is empty. Please upload targets in the Database tab first.")
            st.stop()
            
        df = process_performance_data(perf_file)
        
        # Define levels
        group_key = LEVEL_CONFIG[eval_level]["group_key"]
        unit_col = LEVEL_CONFIG[eval_level]["unit_name"]
        match_key = LEVEL_CONFIG[eval_level]["match_key"]
        
        # 1. Aggregate Performance
        agg_dict = {c: 'sum' for c in ['New_Customers', 'Unique_Customers', 'Active_Customers', 'Dormant_Customers', 'Amount_Collected', 'Disb_Actual'] if c in df.columns}
        agg_dict.update({c: 'mean' for c in ['DD_Plus_7_Pct', 'OTC_Pct', 'Overall_Collection_Pct'] if c in df.columns})

        if eval_level == "Pairs (LO & CO)":
            eval_df = df.groupby(['Branch', 'Pair_ID']).agg(agg_dict).reset_index()
            eval_df['Multiplier'] = 1.0
            m_keys = ['Branch', 'Pair_ID'] if 'Branch' in target_df.columns else ['Pair_ID']
        else:
            unit_counts = df.groupby(group_key)[unit_col].nunique().reset_index(name='Unit_Count')
            eval_df = df.groupby(group_key).agg(agg_dict).reset_index().merge(unit_counts, on=group_key)
            eval_df['Multiplier'] = eval_df['Unit_Count'].astype(float) if eval_level == "Branch Managers" else np.where(eval_df['Unit_Count'] > scale_threshold, eval_df['Unit_Count'] / scale_threshold, 1.0)
            m_keys = [match_key]

        # 2. Merge with MySQL Targets
        eval_df = eval_df.merge(target_df, on=m_keys, how='left').fillna(0)

        # 3. Qualification and Bonus Calculation
        q = eval_df.copy()
        m = q['Multiplier']
        
        for f_key in active_filters:
            if f_key in ["OTC_Pct", "DD_Plus_7_Pct", "Overall_Collection_Pct"]:
                q = q[q[f_key] >= targets[f_key]]
            elif f_key == "disb_threshold":
                q['Disb_Achievement_Pct'] = np.where(q['Disb_Target'] > 0, (q['Disb_Actual'] / q['Disb_Target'] * 100), 0)
                q = q[q['Disb_Achievement_Pct'] >= targets[f_key]]
            else:
                target_col = f"Target_{f_key}"
                goal = q[target_col] * m if target_col in q.columns else targets[f_key] * m
                q = q[q[f_key] >= goal]
                q['Target_Goal'] = goal

        if "Customers" in campaign_name:
            col = campaign_name.replace(" ", "_")
            q['Extra_Bonus_Value'] = np.floor((q[col] - q['Target_Goal']).clip(lower=0) / bonus_step_count) * bonus_step_amount
        elif campaign_name == "Disbursements":
            q['Extra_Bonus_Value'] = np.floor((q['Disb_Achievement_Pct'] - targets["disb_threshold"]).clip(lower=0) / bonus_step_count) * bonus_step_amount
        else:
            q['Extra_Bonus_Value'] = 0.0

        q['Staff_Payout_Amount'] = base_bonus + q['Extra_Bonus_Value']

        # 4. RESTORED: Staff Mapping & Role Splitting Logic
        if eval_level == "Pairs (LO & CO)":
            # Duplicate rows for each role in the pair
            q['Role'] = [['Loan Officer', 'Collections Officer'] for _ in range(len(q))]
            staff_df = q.explode('Role')
            merge_cols = ['Branch', 'Pair_ID', 'Role']
        else:
            staff_df = q.assign(Role=eval_level.rstrip('s').title())
            g_key = group_key if isinstance(group_key, str) else group_key[0]
            merge_cols = [g_key, 'Role']

        if staff_file:
            s_dir = load_staff_directory(staff_file)
            staff_df = staff_df.merge(s_dir.drop_duplicates(merge_cols), on=merge_cols, how='left')
            staff_df['Staff_Name'] = staff_df['Staff_Name'].fillna('Unknown Staff')

        # 5. Final Display and Download
        if not staff_df.empty:
            st.divider()
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Payout", f"KES {staff_df['Staff_Payout_Amount'].sum():,.2f}")
            m2.metric("Qualifying Staff", len(staff_df))
            m3.metric("Avg. Bonus", f"KES {staff_df['Staff_Payout_Amount'].mean():,.2f}")
            
            st.dataframe(staff_df, use_container_width=True)
            
            csv = staff_df.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Download Final Report", data=csv, file_name='UPIA_Incentive_Report.csv', type="primary")
        else:
            st.warning("No staff members qualified with the current settings.")