import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import os

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
DB_NAME = 'upia_targets.db'

def get_db_connection():
    return sqlite3.connect(DB_NAME)

def load_targets_from_db():
    """Reads the current targets from the SQLite database."""
    if not os.path.exists(DB_NAME):
        return pd.DataFrame() # Return empty if DB doesn't exist yet
    
    try:
        conn = get_db_connection()
        df = pd.read_sql_query("SELECT * FROM monthly_targets", conn)
        conn.close()
        return standardize_merge_keys(df)
    except Exception:
        return pd.DataFrame()

# --- 🛡️ ROBUST STRING CLEANER ---
def standardize_merge_keys(df):
    """Aggressively cleans merge keys to prevent disqualification due to typos, spaces, or case mismatches."""
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

# Setup Tabs
tab_calc, tab_db = st.tabs(["📊 Calculator Engine", "🗄️ Monthly Target Database"])

LEVEL_CONFIG = {
    "Pairs (LO & CO)": {"group_key": ["Branch", "Pair_ID"], "unit_name": "Pair_ID", "match_key": "Pair_ID"},
    "Branch Managers": {"group_key": "Branch", "unit_name": "Pair_ID", "match_key": "Branch"},
    "Assistant Sector Managers": {"group_key": "Subsector", "unit_name": "Branch", "match_key": "Subsector"},
    "Sector Managers": {"group_key": "Sector", "unit_name": "Branch", "match_key": "Sector"}
}

st.sidebar.title("Configuration")
eval_level = st.sidebar.selectbox("1. Select Evaluation Level", list(LEVEL_CONFIG.keys()))
campaign_name = st.sidebar.selectbox("2. Select Campaign", ["New Customers", "Unique Customers", "Active Customers", "Dormant Customers", "Collections", "Disbursements"])

st.sidebar.divider() 

# Scaling Logic
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
    with col1:
        bonus_step_count = st.number_input("For every (Qty)", value=2.0, min_value=1.0, step=1.0)
    with col2:
        bonus_step_amount = st.number_input("Pay Extra (KES)", value=200.0, step=50.0)
elif campaign_name == "Disbursements":
    col1, col2 = st.sidebar.columns(2)
    with col1:
        bonus_step_count = st.number_input("For every (X%)", value=1.0, min_value=0.1, step=0.5)
    with col2:
        bonus_step_amount = st.number_input("Pay Extra (KES)", value=200.0, step=50.0)

st.sidebar.divider()
st.sidebar.write("### 🎯 Target Customization")

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
    if st.sidebar.checkbox("Filter by Overall Collection %", value=False):
        targets["Overall_Collection_Pct"] = st.sidebar.number_input("Min Overall Collection (%)", value=95.0)
        active_filters.append("Overall_Collection_Pct")
elif campaign_name == "Disbursements":
    targets["disb_threshold"] = st.sidebar.number_input("Qualification Threshold (%)", value=100.0)
    active_filters.append("disb_threshold")


# ==========================================
# TAB 2: DATABASE MANAGEMENT
# ==========================================
with tab_db:
    st.header("🗄️ Manage Monthly Targets")
    st.write("Upload a new Target CSV to overwrite the current database. This will be used as the master target list for calculations.")
    
    new_db_file = st.file_uploader("Upload New Master Targets CSV", type=['csv'], key="db_uploader")
    
    if new_db_file:
        raw_db_df = pd.read_csv(new_db_file)
        raw_db_df.columns = [str(c).strip().replace(' ', '_') for c in raw_db_df.columns]
        raw_db_df = raw_db_df.loc[:, ~raw_db_df.columns.str.contains('^Unnamed', case=False, na=False)]
        
        # Clean numeric targets
        for col in raw_db_df.columns:
            if col not in ['Pair_ID', 'Branch', 'Subsector', 'Sector']:
                raw_db_df[col] = pd.to_numeric(
                    raw_db_df[col].astype(str).replace(r'[^-0-9.]', '', regex=True), 
                    errors='coerce'
                ).fillna(0)
                
        clean_db_df = standardize_merge_keys(raw_db_df)
        
        # Save to SQLite
        try:
            conn = get_db_connection()
            clean_db_df.to_sql('monthly_targets', conn, if_exists='replace', index=False)
            conn.close()
            st.success("✅ Master Target Database successfully updated!")
        except Exception as e:
            st.error(f"Failed to update database: {e}")

    st.divider()
    
    st.subheader("Current Database View")
    current_db = load_targets_from_db()
    
    if current_db.empty:
        st.warning("The database is currently empty. Please upload a Target CSV above to initialize it.")
    else:
        st.metric("Total Stored Entities", len(current_db))
        st.dataframe(current_db, use_container_width=True)


# ==========================================
# TAB 1: CALCULATOR ENGINE
# ==========================================
with tab_calc:
    st.write(f"**Level:** {eval_level} | **Campaign:** {campaign_name}")
    
    c1, c2 = st.columns(2)
    with c1: perf_file = st.file_uploader("1. Upload Actuals CSV", type=['csv'])
    with c2: staff_file = st.file_uploader("2. Upload Staff Directory CSV", type=['csv'])

    if perf_file:
        target_df = load_targets_from_db()
        
        if target_df.empty:
            st.error("🚨 The Target Database is empty. Please go to the 'Monthly Target Database' tab and upload your targets first.")
            st.stop()
            
        try:
            df = process_performance_data(perf_file)
            
            with st.expander("🔍 Preview Actuals Data"):
                st.dataframe(df.head(5))
            
            # --- 🛡️ Null Pair Validation ---
            if 'Pair_ID' in df.columns:
                if df['Pair_ID'].isnull().any() or (df['Pair_ID'] == '').any():
                    st.error("🚨 Null/Blank Pair detected in Actuals. Please Align Pairing correctly")
                    st.stop()
            
            group_key = LEVEL_CONFIG[eval_level]["group_key"]
            unit_col = LEVEL_CONFIG[eval_level]["unit_name"]
            match_key = LEVEL_CONFIG[eval_level]["match_key"]
            
            # --- 📈 1. AGGREGATE ACTUALS ---
            agg_dict = {c: 'sum' for c in ['New_Customers', 'Unique_Customers', 'Active_Customers', 'Dormant_Customers', 'Amount_Collected', 'Disb_Actual'] if c in df.columns}
            agg_dict.update({c: 'mean' for c in ['DD_Plus_7_Pct', 'OTC_Pct', 'Overall_Collection_Pct'] if c in df.columns})

            if eval_level == "Pairs (LO & CO)":
                if 'Branch' not in df.columns or 'Pair_ID' not in df.columns:
                    st.error("🚨 'Branch' and 'Pair_ID' columns are required in Actuals for Pairs evaluation.")
                    st.stop()
                    
                eval_df = df.groupby(['Branch', 'Pair_ID']).agg(agg_dict).reset_index()
                eval_df['Multiplier'] = 1.0
                merge_keys = ['Branch', 'Pair_ID'] if 'Branch' in target_df.columns else ['Pair_ID']
                
            else:
                unit_counts = df.groupby(group_key)[unit_col].nunique().reset_index(name='Unit_Count')
                eval_df = df.groupby(group_key).agg(agg_dict).reset_index().merge(unit_counts, on=group_key)
                eval_df['Multiplier'] = eval_df['Unit_Count'].astype(float) if eval_level == "Branch Managers" else np.where(eval_df['Unit_Count'] > scale_threshold, eval_df['Unit_Count'] / scale_threshold, 1.0)
                merge_keys = [match_key]

            for mk in merge_keys:
                if mk in eval_df.columns: eval_df[mk] = eval_df[mk].astype(str)
                if mk in target_df.columns: target_df[mk] = target_df[mk].astype(str)
            
            # --- 🎯 2. AGGREGATE TARGETS ---
            missing_t_keys = [k for k in merge_keys if k not in target_df.columns]
            if missing_t_keys:
                st.error(f"🚨 Missing required column in Targets Database: {missing_t_keys}. The Database must contain the column you are evaluating against.")
                st.stop()
                
            target_num_cols = target_df.select_dtypes(include=[np.number]).columns.tolist()
            t_sum_cols = [c for c in target_num_cols if 'Pct' not in c and c not in merge_keys]
            t_mean_cols = [c for c in target_num_cols if 'Pct' in c and c not in merge_keys]

            target_agg_dict = {}
            for c in t_sum_cols: target_agg_dict[c] = 'sum'
            for c in t_mean_cols: target_agg_dict[c] = 'mean'

            if target_agg_dict:
                target_df_clean = target_df.groupby(merge_keys).agg(target_agg_dict).reset_index()
            else:
                target_df_clean = target_df.drop_duplicates(subset=merge_keys)

            # Merge rolled-up targets into the rolled-up actuals
            eval_df = eval_df.merge(target_df_clean, on=merge_keys, how='left').fillna(0)

            # --- Enhanced Missing Target Warning ---
            if 'Disb_Target' in eval_df.columns and campaign_name == "Disbursements":
                missing_targets = eval_df[eval_df['Disb_Target'] == 0]
                if not missing_targets.empty:
                    if len(merge_keys) == 2:
                        missing_entities = missing_targets[merge_keys[0]].astype(str) + " (" + missing_targets[merge_keys[1]].astype(str) + ")"
                    else:
                        missing_entities = missing_targets[merge_keys[0]].astype(str)
                    
                    missing_str = ", ".join(missing_entities.tolist())
                    st.warning(f"⚠️ **Missing targets for {len(missing_targets)} entities:**\n\n{missing_str}\n\n*These entities will be evaluated against a target of 0. Check your Target Database to ensure they exist.*")

            # --- Calculation Engine ---
            q = eval_df.copy()
            m = q['Multiplier']
            
            for filter_key in active_filters:
                if filter_key in ["OTC_Pct", "DD_Plus_7_Pct", "Overall_Collection_Pct"]:
                    q = q[q[filter_key] >= targets[filter_key]]
                
                elif filter_key == "disb_threshold":
                    if 'Disb_Target' not in q.columns:
                        st.error("🚨 Missing 'Disb_Target' column in Targets Database.")
                        st.stop()
                    
                    q['Disb_Achievement_Pct'] = np.where(q['Disb_Target'] > 0, (q['Disb_Actual'] / q['Disb_Target'] * 100), 0)
                    q = q[q['Disb_Achievement_Pct'] >= targets[filter_key]]
                
                else:
                    target_col = f"Target_{filter_key}"
                    if target_col in q.columns:
                        q['Target_Goal'] = q[target_col] * m 
                    else:
                        q['Target_Goal'] = targets[filter_key] * m 
                    
                    q = q[q[filter_key] >= q['Target_Goal']]

            if "Customers" in campaign_name:
                col = campaign_name.replace(" ", "_")
                q['Extra_Achieved'] = (q[col] - q['Target_Goal']).clip(lower=0)
                q['Extra_Bonus_Value'] = np.floor(q['Extra_Achieved'] / bonus_step_count) * bonus_step_amount
            
            elif campaign_name == "Disbursements":
                q['Pct_Above_Threshold'] = (q['Disb_Achievement_Pct'] - targets["disb_threshold"]).clip(lower=0)
                q['Extra_Bonus_Value'] = np.floor(q['Pct_Above_Threshold'] / bonus_step_count) * bonus_step_amount
            
            else:
                q['Extra_Bonus_Value'] = 0.0

            q['Base_Bonus'] = base_bonus
            q['Staff_Payout_Amount'] = q['Base_Bonus'] + q['Extra_Bonus_Value']

            # --- Staff Mapping ---
            if eval_level == "Pairs (LO & CO)":
                q['Role'] = [['Loan Officer', 'Collections Officer'] for _ in range(len(q))]
                staff_df = q.explode('Role')
                m_keys = ['Branch', 'Pair_ID', 'Role']
            else:
                staff_df = q.assign(Role=eval_level.rstrip('s').title())
                g_key = group_key if isinstance(group_key, str) else group_key[0] 
                m_keys = [g_key, 'Role']

            if staff_file:
                s_dir = load_staff_directory(staff_file)
                staff_df = staff_df.merge(s_dir.drop_duplicates(m_keys), on=m_keys, how='left')
                if 'Staff_Name' in staff_df.columns:
                    staff_df['Staff_Name'] = staff_df['Staff_Name'].fillna('Unknown Staff')

            # Formatting Output Columns
            if campaign_name == "Disbursements" and not staff_df.empty:
                cols = list(staff_df.columns)
                if 'Disb_Actual' in cols and 'Disb_Achievement_Pct' in cols:
                    cols.remove('Disb_Achievement_Pct')
                    idx = cols.index('Disb_Actual') + 1
                    
                    if 'Disb_Target' in cols:
                        cols.remove('Disb_Target')
                        cols.insert(idx, 'Disb_Target')
                        idx += 1
                    
                    cols.insert(idx, 'Disb_Achievement_Pct')
                    staff_df = staff_df[cols]

            # --- Final Display ---
            if not staff_df.empty:
                st.divider()
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Payout", f"KES {staff_df['Staff_Payout_Amount'].sum():,.2f}")
                m2.metric("Qualifying Staff", len(staff_df))
                m3.metric("Avg. Bonus", f"KES {staff_df['Staff_Payout_Amount'].mean():,.2f}")
                
                st.dataframe(
                    staff_df, 
                    use_container_width=True,
                    column_config={"Pair_ID": st.column_config.TextColumn("Pair ID", width="small")}
                )
                
                csv = staff_df.to_csv(index=False).encode('utf-8')
                st.download_button("⬇️ Download Final Report", data=csv, file_name=f'Incentive_Report.csv', mime='text/csv', type="primary")
            else:
                st.warning("No staff members qualified with the selected criteria.")

        except Exception as e:
            st.error(f"Error processing calculation: {e}")