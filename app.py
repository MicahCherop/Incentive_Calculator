import streamlit as st
import pandas as pd
import numpy as np
import urllib.parse
from sqlalchemy import create_engine, text
from datetime import datetime

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

# --- 🗄️ DATABASE MANAGEMENT ---
def get_db_engine():
    if "mysql" not in st.secrets:
        return None, "Missing [mysql] section in Secrets."
    try:
        s = st.secrets["mysql"]
        safe_pass = urllib.parse.quote_plus(s["password"])
        conn_str = f"mysql+pymysql://{s['user']}:{safe_pass}@{s['host']}:{s['port']}/{s['database']}"
        return create_engine(conn_str), None
    except Exception as e:
        return None, str(e)

def load_targets_from_db():
    engine, error = get_db_engine()
    if error: return pd.DataFrame()
    try:
        df = pd.read_sql_table("monthly_targets", con=engine)
        return standardize_merge_keys(df)
    except: return pd.DataFrame()

def save_targets_to_db(df):
    engine, error = get_db_engine()
    if error: 
        st.error(f"Database Error: {error}")
        return
    try:
        # Create Unique_ID if missing
        if 'Unique_ID' not in df.columns:
            df['Unique_ID'] = df['Branch'].astype(str) + "_" + df['Pair_ID'].astype(str)
        df.to_sql('monthly_targets', engine, if_exists='replace', index=False)
        st.success("✅ Targets database updated successfully!")
    except Exception as e:
        st.error(f"Failed to save targets: {e}")

def log_payout_event(df, campaigns, level):
    engine, error = get_db_engine()
    if error or df.empty: return False
    try:
        history_df = df.copy()
        history_df['Calculation_Date'] = datetime.now().date()
        history_df['Campaign_Type'] = ", ".join(campaigns)
        history_df['Eval_Level'] = level
        if 'Unique_ID' in history_df.columns:
            history_df['Unique_ID'] = history_df['Unique_ID'].astype(str)
        history_df.to_sql('payout_history', engine, if_exists='append', index=False)
        return True
    except Exception as e:
        st.error(f"Autosave failed: {e}")
        return False

# --- 🛡️ STRING CLEANER ---
def standardize_merge_keys(df):
    for col in ['Branch', 'Subsector', 'Sector', 'Role']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.title().replace({'Nan': np.nan, 'None': np.nan})
    if 'Pair_ID' in df.columns:
        df['Pair_ID'] = df['Pair_ID'].astype(str).str.strip().str.upper().str.replace(r'\.0$', '', regex=True)
    return df

# --- 📊 DATA HELPERS ---
@st.cache_data
def process_performance_data(file):
    df = pd.read_csv(file)
    df.columns = [str(c).strip().replace(' ', '_') for c in df.columns]
    num_cols = ['New_Customers', 'Unique_Customers', 'Active_Customers', 'Dormant_Customers', 'Amount_Collected', 'DD_Plus_7_Pct', 'OTC_Pct', 'Overall_Collection_Pct', 'Disb_Actual', 'Disb_Target']
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).replace(r'[^-0-9.]', '', regex=True), errors='coerce').fillna(0)
    return standardize_merge_keys(df)

@st.cache_data
def load_staff_directory(file):
    df = pd.read_csv(file, dtype={'Phone_Number': str, 'Pair_ID': str})
    df.columns = [str(c).strip().replace(' ', '_') for c in df.columns]
    return standardize_merge_keys(df)

# --- 🏢 MAIN INTERFACE ---
st.title("UPIA Incentive System 🏢")
tab_calc, tab_db, tab_history = st.tabs(["📊 Calculator Engine", "🗄️ Target Database", "📜 Payout History"])

LEVEL_CONFIG = {
    "Pairs (LO & CO)": {"group_key": ["Branch", "Pair_ID"], "unit_name": "Pair_ID", "match_key": "Pair_ID"},
    "Branch Managers": {"group_key": "Branch", "unit_name": "Pair_ID", "match_key": "Branch"},
    "Assistant Sector Managers": {"group_key": "Subsector", "unit_name": "Branch", "match_key": "Subsector"},
    "Sector Managers": {"group_key": "Sector", "unit_name": "Branch", "match_key": "Sector"}
}

# --- 🛠️ SIDEBAR ---
st.sidebar.title("Configuration")
eval_level = st.sidebar.selectbox("1. Select Evaluation Level", list(LEVEL_CONFIG.keys()))
selected_campaigns = st.sidebar.multiselect(
    "2. Select Campaigns", 
    ["New Customers", "Unique Customers", "Active Customers", "Dormant Customers", "Collections", "Disbursements"],
    default=["New Customers"]
)

st.sidebar.divider()
st.sidebar.subheader("🚩 Threshold Requirements")
campaign_targets = {}
for campaign in selected_campaigns:
    key = campaign.replace(" ", "_")
    if campaign == "Disbursements":
        # Fixed at 100% default per requirement
        campaign_targets[f"{key}_min"] = st.sidebar.number_input(f"Min Disbursement Achievement (%)", value=100.0, key=f"min_{key}")
    else:
        campaign_targets[f"{key}_min"] = st.sidebar.number_input(f"Min {campaign} Required", value=5.0, key=f"min_{key}")

st.sidebar.divider()
st.sidebar.subheader("💵 Payout Settings")
base_bonus = st.sidebar.number_input("Base Bonus Amount (KES)", value=3000.0, step=500.0)

for campaign in selected_campaigns:
    key = campaign.replace(" ", "_")
    st.sidebar.write(f"*{campaign} Extra Bonus*")
    col1, col2 = st.sidebar.columns(2)
    if campaign == "Disbursements":
        with col1: campaign_targets[f"{key}_step"] = st.number_input("For every (X%)", value=1.0, key=f"step_{key}")
    else:
        with col1: campaign_targets[f"{key}_step"] = st.number_input("For every (Qty)", value=1.0, key=f"step_{key}")
    with col2: campaign_targets[f"{key}_amt"] = st.number_input("Pay Extra (KES)", value=200.0, key=f"amt_{key}")

# ==========================================
# TAB 1: CALCULATOR ENGINE
# ==========================================
with tab_calc:
    st.header("📊 Calculator Engine")
    c1, c2 = st.columns(2)
    with c1: perf_file = st.file_uploader("1. Upload Actuals CSV", type=['csv'], key="calc_perf")
    with c2: staff_file = st.file_uploader("2. Upload Staff Directory CSV", type=['csv'], key="calc_staff")

    if perf_file:
        target_df = load_targets_from_db()
        df = process_performance_data(perf_file)
        
        group_key = LEVEL_CONFIG[eval_level]["group_key"]
        unit_col = LEVEL_CONFIG[eval_level]["unit_name"]
        match_key = LEVEL_CONFIG[eval_level]["match_key"]
        
        # Aggregate logic
        agg_dict = {c: 'sum' for c in ['New_Customers', 'Unique_Customers', 'Active_Customers', 'Dormant_Customers', 'Amount_Collected', 'Disb_Actual', 'Disb_Target'] if c in df.columns}
        agg_dict.update({c: 'mean' for c in ['DD_Plus_7_Pct', 'OTC_Pct', 'Overall_Collection_Pct'] if c in df.columns})

        if eval_level == "Pairs (LO & CO)":
            eval_df = df.groupby(['Branch', 'Pair_ID']).agg(agg_dict).reset_index()
            eval_df['Multiplier'] = 1.0
            m_keys = ['Branch', 'Pair_ID']
        else:
            unit_counts = df.groupby(group_key)[unit_col].nunique().reset_index(name='Unit_Count')
            eval_df = df.groupby(group_key).agg(agg_dict).reset_index().merge(unit_counts, on=group_key)
            eval_df['Multiplier'] = eval_df['Unit_Count'].astype(float)
            m_keys = [match_key]

        eval_df = eval_df.merge(target_df, on=m_keys, how='left').fillna(0)
        q = eval_df.copy()
        
        q['Total_Extra_Bonus'] = 0.0
        qualified_mask = pd.Series([False] * len(q))

        for campaign in selected_campaigns:
            col = campaign.replace(" ", "_")
            if campaign == "Disbursements":
                # Priority: Use DB Disb_Target if it exists, else assume achievement % is based on 100
                if 'Disb_Target' in q.columns and (q['Disb_Target'] > 0).any():
                    q['Disb_Achievement_Pct'] = (q['Disb_Actual'] / q['Disb_Target']) * 100
                else:
                    q['Disb_Achievement_Pct'] = q['Disb_Actual'] # Fallback if only achievement is uploaded
                
                goal = campaign_targets[f"{col}_min"]
                qualified_mask = qualified_mask | (q['Disb_Achievement_Pct'] >= goal)
                diff = (q['Disb_Achievement_Pct'] - goal).clip(lower=0)
                q[f"Bonus_{col}"] = np.floor(diff / campaign_targets[f"{col}_step"]) * campaign_targets[f"{col}_amt"]
                q['Total_Extra_Bonus'] += q[f"Bonus_{col}"]
            elif col in q.columns:
                target_col = f"Target_{col}"
                goal = (q[target_col] if target_col in q.columns else campaign_targets[f"{col}_min"]) * q['Multiplier']
                qualified_mask = qualified_mask | (q[col] >= goal)
                diff = (q[col] - goal).clip(lower=0)
                q[f"Bonus_{col}"] = np.floor(diff / campaign_targets[f"{col}_step"]) * campaign_targets[f"{col}_amt"]
                q['Total_Extra_Bonus'] += q[f"Bonus_{col}"]

        q = q[qualified_mask]

        if not q.empty:
            q['Staff_Payout_Amount'] = base_bonus + q['Total_Extra_Bonus']
            q['Net_Payout_Amount'] = q['Staff_Payout_Amount'] * 0.70

            # Merge Staff Names
            staff_df = q.assign(Role=eval_level.rstrip('s').title()) if eval_level != "Pairs (LO & CO)" else q.assign(Role=[['Loan Officer', 'Collections Officer']]*len(q)).explode('Role')
            if staff_file:
                s_dir = load_staff_directory(staff_file)
                merge_cols = ['Branch', 'Pair_ID', 'Role'] if eval_level == "Pairs (LO & CO)" else [group_key if isinstance(group_key, str) else group_key[0], 'Role']
                staff_df = staff_df.merge(s_dir.drop_duplicates(merge_cols), on=merge_cols, how='left')

            st.divider()
            m1, m2, m3 = st.columns(3)
            m1.metric("Gross Total", f"KES {staff_df['Staff_Payout_Amount'].sum():,.0f}")
            m2.metric("Net (70%) Total", f"KES {staff_df['Net_Payout_Amount'].sum():,.0f}")
            m3.metric("Qualified Staff", len(staff_df))
            
            # --- CHARTS ---
            c1, c2 = st.columns(2)
            with c1: st.write("**Payout by Branch**"); st.bar_chart(staff_df.groupby('Branch')['Staff_Payout_Amount'].sum())
            with c2: st.write("**Payout by Role**"); st.bar_chart(staff_df.groupby('Role')['Staff_Payout_Amount'].sum())

            st.dataframe(staff_df, use_container_width=True)
            if st.button("💾 Finalize & Save History", type="primary"):
                if log_payout_event(staff_df, selected_campaigns, eval_level):
                    st.success("✅ Saved!")

# ==========================================
# TAB 2: TARGET DATABASE (REINSTATED UPLOAD)
# ==========================================
with tab_db:
    st.header("🗄️ Target Database Management")
    
    # 🟢 NEW: Restore Target Upload
    with st.expander("⬆️ Upload New Targets (CSV)"):
        target_upload = st.file_uploader("Choose Target CSV file", type=['csv'], key="target_csv_uploader")
        if target_upload:
            new_target_df = pd.read_csv(target_upload)
            st.write("Preview of Uploaded Targets:")
            st.dataframe(new_target_df.head())
            if st.button("Overwrite Database with this File"):
                save_targets_to_db(new_target_df)
    
    st.divider()
    db_view = load_targets_from_db()
    if not db_view.empty:
        st.dataframe(db_view, use_container_width=True, column_config={"Unique_ID": None})
    else:
        st.warning("Database is empty. Please upload a target CSV above.")

# ==========================================
# TAB 3: HISTORY
# ==========================================
with tab_history:
    st.header("📜 Payout History")
    h1, h2 = st.columns(2)
    with h1: sd = st.date_input("Start", value=datetime.now())
    with h2: ed = st.date_input("End", value=datetime.now())
    
    engine, _ = get_db_engine()
    if engine:
        query = text("SELECT * FROM payout_history WHERE Calculation_Date BETWEEN :s AND :e")
        try:
            hist_df = pd.read_sql(query, engine, params={"s": sd, "e": ed})
            if not hist_df.empty:
                st.line_chart(hist_df.groupby('Calculation_Date')['Staff_Payout_Amount'].sum())
                st.dataframe(hist_df, use_container_width=True, column_config={"Unique_ID": None})
        except: st.info("No history found.")