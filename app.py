import streamlit as st
import pandas as pd
import numpy as np

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

if "current_page" not in st.session_state:
    st.session_state.current_page = "calculator"

# 3. Helper Functions
def clean_numeric(series):
    return pd.to_numeric(
        series.astype(str).replace(r'[^-0-9.]', '', regex=True), 
        errors='coerce'
    ).fillna(0)

# 4. Navigation
st.sidebar.title("Navigation")
if st.session_state.current_page == "calculator":
    if st.sidebar.button("⚙️ Open Admin Dashboard", use_container_width=True):
        st.session_state.current_page = "admin"
        st.rerun()
else:
    if st.sidebar.button("⬅️ Back to Calculator", use_container_width=True):
        st.session_state.current_page = "calculator"
        st.rerun()

st.sidebar.divider()

if st.session_state.current_page == "admin":
    st.title("⚙️ User Management Dashboard")
    col1, col2 = st.columns(2)
    with col1:
        new_role = st.selectbox("User Role", ["UPIA OpsAdmin", "Finance Officer"])
        new_user = st.text_input("Username")
    with col2:
        new_pass = st.text_input("Password", type="password")
    
    if st.button("Generate Secure Access Code", type="primary"):
        if new_user and new_pass:
            st.success("✅ Code generated!")
            st.code(f'# {new_role}\n{new_user} = "{new_pass}"', language="toml")

else:
    st.title("UPIA Incentive System 🏢")
    
    LEVEL_CONFIG = {
        "Pairs (LO & CO)": {"group_key": None, "unit_name": "Pair"},
        "Branch Managers": {"group_key": "Branch", "unit_name": "Pair_ID"},
        "Assistant Sector Managers": {"group_key": "Subsector", "unit_name": "Branch"},
        "Sector Managers": {"group_key": "Sector", "unit_name": "Branch"}
    }

    st.sidebar.title("Configuration")
    eval_level = st.sidebar.selectbox("1. Select Evaluation Level", list(LEVEL_CONFIG.keys()))
    campaign_name = st.sidebar.selectbox("2. Select Campaign", ["New Customers", "Unique Customers", "Active Customers", "Dormant Customers", "Collections", "Disbursements"])

    st.sidebar.divider() 
    
    # Scaling Logic for aggregate levels
    scale_threshold = 1
    if eval_level == "Assistant Sector Managers": 
        scale_threshold = st.sidebar.number_input("Standard ASM Branch Count", value=4)
    elif eval_level == "Sector Managers": 
        scale_threshold = st.sidebar.number_input("Standard Sector Branch Count", value=25)

    st.sidebar.write("### 💵 Payout Settings")
    base_bonus = st.sidebar.number_input("Base Bonus KES", value=3000.0, step=500.0)
    
    # Context-aware bonus settings
    incremental_bonus = 0.0
    disb_inc_rate = 1.0 
    disb_bonus_step = 0.0

    if "Customers" in campaign_name:
        incremental_bonus = st.sidebar.number_input("Extra Bonus (Per 2 Extra)", value=200.0, step=100.0)
    elif campaign_name == "Disbursements":
        disb_inc_rate = st.sidebar.number_input("Step: For every X% extra...", value=1.0, step=0.5, help="Example: For every 2.0% above target")
        disb_bonus_step = st.sidebar.number_input("...Add this amount (KES)", value=200.0, step=50.0)

    st.sidebar.divider()
    st.sidebar.write("### 🎯 Target Customization")
    
    targets = {"New_Customers": 0.0, "Unique_Customers": 0.0, "Active_Customers": 0.0, "Dormant_Customers": 0.0, "coll_amt": 0.0, "dd7": 0.0, "otc": 0.0, "disb_threshold": 0.0}
    
    if "Customers" in campaign_name:
        key = campaign_name.replace(" ", "_")
        targets[key] = st.sidebar.number_input(f"Base Min {campaign_name}", value=6.0)
    elif campaign_name == "Collections":
        targets["coll_amt"] = st.sidebar.number_input("Base Min Amount", value=50000.0)
        targets["dd7"] = st.sidebar.number_input("Min DD+7 (%)", value=94.0)
        targets["otc"] = st.sidebar.number_input("Min OTC (%)", value=91.0)
    elif campaign_name == "Disbursements":
        targets["disb_threshold"] = st.sidebar.number_input("Qualification Threshold (%)", value=100.0, help="Min percentage of target achieved to qualify for bonus.")

    # File Uploaders
    st.write(f"**Level:** {eval_level} | **Campaign:** {campaign_name}")
    c1, c2 = st.columns(2)
    with c1: perf_file = st.file_uploader("1. Upload Performance CSV (Include Target_Amt & Actual_Amt for Disbursements)", type=['csv'])
    with c2: staff_file = st.file_uploader("2. Upload Staff Directory CSV", type=['csv'])

    if perf_file:
        try:
            df = pd.read_csv(perf_file)
            
            # Cleaning common columns
            num_cols = ['New_Customers', 'Unique_Customers', 'Active_Customers', 'Dormant_Customers', 
                        'Amount_Collected', 'DD_Plus_7_Pct', 'OTC_Pct', 'Disb_Target', 'Disb_Actual']
            for col in num_cols:
                if col in df.columns:
                    df[col] = clean_numeric(df[col])
            
            # Level Aggregation logic
            group_key = LEVEL_CONFIG[eval_level]["group_key"]
            unit_col = LEVEL_CONFIG[eval_level]["unit_name"]
            
            if group_key:
                unit_counts = df.groupby(group_key)[unit_col].nunique().reset_index(name='Unit_Count')
                # Summing totals, averaging percentages
                agg_dict = {c: 'sum' for c in ['New_Customers', 'Unique_Customers', 'Active_Customers', 'Dormant_Customers', 'Amount_Collected', 'Disb_Target', 'Disb_Actual'] if c in df.columns}
                agg_dict.update({c: 'mean' for c in ['DD_Plus_7_Pct', 'OTC_Pct'] if c in df.columns})
                eval_df = df.groupby(group_key).agg(agg_dict).reset_index().merge(unit_counts, on=group_key)
                
                # Multiplier logic
                if eval_level == "Branch Managers":
                    eval_df['Multiplier'] = eval_df['Unit_Count'].astype(float)
                else:
                    eval_df['Multiplier'] = np.where(eval_df['Unit_Count'] > scale_threshold, eval_df['Unit_Count'] / scale_threshold, 1.0)
            else:
                eval_df = df.copy()
                eval_df['Multiplier'] = 1.0

            # --- Calculation Engine ---
            q = eval_df.copy()
            m = q['Multiplier']
            
            if "Customers" in campaign_name:
                col = campaign_name.replace(" ", "_")
                q = q[q[col] >= (targets[col] * m)]
                q['Extra_Achieved'] = (q[col] - (targets[col] * m)).clip(lower=0)
                q['Extra_Bonus_Value'] = np.floor(q['Extra_Achieved'] / 2) * incremental_bonus
                
            elif campaign_name == "Collections":
                q = q[(q['Amount_Collected'] >= (targets["coll_amt"] * m)) & 
                      (q['DD_Plus_7_Pct'] >= targets["dd7"]) & 
                      (q['OTC_Pct'] >= targets["otc"])]
                q['Extra_Bonus_Value'] = 0.0
                
            elif campaign_name == "Disbursements":
                # Calculate % from data
                q['Disb_Achievement_Pct'] = (q['Disb_Actual'] / q['Disb_Target'] * 100).fillna(0)
                # Qualification filter
                q = q[q['Disb_Achievement_Pct'] >= targets["disb_threshold"]]
                # Extra Bonus logic
                q['Pct_Above_Threshold'] = (q['Disb_Achievement_Pct'] - targets["disb_threshold"]).clip(lower=0)
                q['Extra_Bonus_Value'] = np.floor(q['Pct_Above_Threshold'] / disb_inc_rate) * disb_bonus_step

            q['Base_Bonus'] = base_bonus
            q['Staff_Payout_Amount'] = q['Base_Bonus'] + q.get('Extra_Bonus_Value', 0)

            # Map to Staff
            if eval_level == "Pairs (LO & CO)":
                q['Role'] = [['Loan Officer', 'Collections Officer'] for _ in range(len(q))]
                staff_df = q.explode('Role')
                merge_keys = ['Branch', 'Pair_ID', 'Role']
            else:
                staff_df = q.assign(Role=eval_level.rstrip('s'))
                merge_keys = [group_key, 'Role']

            if staff_file:
                s_dir = pd.read_csv(staff_file, dtype={'Phone_Number': str, 'Pair_ID': str})
                staff_df = staff_df.merge(s_dir.drop_duplicates(merge_keys), on=merge_keys, how='left')

            # --- Metrics & Results ---
            if not staff_df.empty:
                st.divider()
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Payout", f"${staff_df['Staff_Payout_Amount'].sum():,.2f}")
                c2.metric("Qualifying Staff", len(staff_df))
                c3.metric("Avg. Bonus", f"${staff_df['Staff_Payout_Amount'].mean():,.2f}")

                st.dataframe(staff_df, use_container_width=True)
                
                csv = staff_df.to_csv(index=False).encode('utf-8')
                st.download_button("⬇️ Download Report", data=csv, file_name=f'Payouts_{campaign_name}.csv', mime='text/csv', type="primary")
            else:
                st.warning("No staff met the requirements for this campaign selection.")

        except Exception as e:
            st.error(f"Error: {e}")