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

# 2. State Management
if "current_page" not in st.session_state:
    st.session_state.current_page = "calculator"

# 3. Helper Functions
def clean_numeric(series):
    """Clean currency, percentages, and commas from strings and return floats."""
    return pd.to_numeric(
        series.astype(str).replace(r'[^-0-9.]', '', regex=True), 
        errors='coerce'
    ).fillna(0)

# 4. Navigation Sidebar
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

# --- ADMIN PAGE ---
if st.session_state.current_page == "admin":
    st.title("⚙️ User Management Dashboard")
    st.info("Note: This interface simulates access code generation for local configuration.")
    col1, col2 = st.columns(2)
    with col1:
        new_role = st.selectbox("User Role", ["UPIA OpsAdmin", "Finance Officer"])
        new_user = st.text_input("Username")
    with col2:
        new_pass = st.text_input("Password", type="password")
    
    if st.button("Generate Secure Access Code", type="primary"):
        if new_user and new_pass:
            st.success("✅ Access snippet generated! Copy this to your secrets file.")
            st.code(f'# {new_role}\n{new_user} = "{new_pass}"', language="toml")

# --- CALCULATOR PAGE ---
else:
    st.title("UPIA Incentive System 🏢")
    
    # Configuration Mapping
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
    
    # Scaling Logic
    scale_threshold = 1
    if eval_level == "Assistant Sector Managers": 
        scale_threshold = st.sidebar.number_input("Standard ASM Branch Count", value=4)
    elif eval_level == "Sector Managers": 
        scale_threshold = st.sidebar.number_input("Standard Sector Branch Count", value=25)

    st.sidebar.write("### 💵 Payout Settings")
    base_bonus = st.sidebar.number_input("Base Bonus", value=3000.0, step=500.0)
    
    # Context-aware bonus settings
    incremental_bonus = 0.0
    disbursement_bonus_step = 0.0
    disb_inc_rate = 1.0 

    if campaign_name in ["New Customers", "Unique Customers", "Active Customers", "Dormant Customers"]:
        incremental_bonus = st.sidebar.number_input("Extra Bonus (Per 2 Extra)", value=200.0, step=100.0)
    elif campaign_name == "Disbursements":
        disb_inc_rate = st.sidebar.number_input("Reward for every X% extra", value=1.0, step=0.5)
        disbursement_bonus_step = st.sidebar.number_input(f"Extra Bonus (Per {disb_inc_rate}% Extra)", value=200.0, step=50.0)

    st.sidebar.divider()
    st.sidebar.write("### 🎯 Target Customization")
    # Initialize targets
    targets = {"New_Customers": 0.0, "Unique_Customers": 0.0, "Active_Customers": 0.0, "Dormant_Customers": 0.0, "coll_amt": 0.0, "dd7": 0.0, "otc": 0.0, "disb": 0.0}
    
    if "Customers" in campaign_name:
        key = campaign_name.replace(" ", "_")
        targets[key] = st.sidebar.number_input(f"Base Min {campaign_name}", value=6.0)
    elif campaign_name == "Collections":
        use_coll_amt = st.sidebar.checkbox("Apply Min Collection Amount", value=True)
        if use_coll_amt: targets["coll_amt"] = st.sidebar.number_input("Base Min Amount", value=50000.0)
        use_dd7 = st.sidebar.checkbox("Apply Min DD+7 (%)", value=True)
        if use_dd7: targets["dd7"] = st.sidebar.number_input("Min DD+7 (%)", value=94.0)
        use_otc = st.sidebar.checkbox("Apply Min OTC (%)", value=True)
        if use_otc: targets["otc"] = st.sidebar.number_input("Min OTC (%)", value=91.0)
    elif campaign_name == "Disbursements":
        targets["disb"] = st.sidebar.number_input("Min Disbursement (%)", value=100.0)

    # File Uploaders
    st.write(f"**Level:** {eval_level} | **Campaign:** {campaign_name}")
    c1, c2 = st.columns(2)
    with c1: perf_file = st.file_uploader("1. Upload Performance CSV", type=['csv'])
    with c2: staff_file = st.file_uploader("2. Upload Staff Directory CSV", type=['csv'])

    if perf_file:
        try:
            df = pd.read_csv(perf_file)
            
            # Use robust cleaning function
            num_cols = ['New_Customers', 'Unique_Customers', 'Active_Customers', 'Dormant_Customers', 'Amount_Collected', 'DD_Plus_7_Pct', 'OTC_Pct', 'Disbursements']
            for col in num_cols:
                if col in df.columns:
                    df[col] = clean_numeric(df[col])
            
            # Aggregate based on Level
            eval_df = df.copy()
            group_key = LEVEL_CONFIG[eval_level]["group_key"]
            unit_col = LEVEL_CONFIG[eval_level]["unit_name"]
            
            if group_key:
                unit_counts = df.groupby(group_key)[unit_col].nunique().reset_index(name='Unit_Count')
                agg = {c: 'sum' for c in ['New_Customers', 'Unique_Customers', 'Active_Customers', 'Dormant_Customers', 'Amount_Collected'] if c in df.columns}
                agg.update({c: 'mean' for c in ['DD_Plus_7_Pct', 'OTC_Pct', 'Disbursements'] if c in df.columns})
                eval_df = df.groupby(group_key).agg(agg).reset_index().merge(unit_counts, on=group_key)
                
                if eval_level == "Branch Managers":
                    eval_df['Multiplier'] = eval_df['Unit_Count'].astype(float)
                else:
                    eval_df['Multiplier'] = np.where(eval_df['Unit_Count'] > scale_threshold, eval_df['Unit_Count'] / scale_threshold, 1.0)
            else:
                eval_df['Multiplier'] = 1.0

            # Filtering Logic
            q = eval_df.copy()
            m = q['Multiplier']
            
            if "Customers" in campaign_name:
                col = campaign_name.replace(" ", "_")
                q = q[q[col] >= (targets[col] * m)]
                q['Extra_Achieved'] = (q[col] - (targets[col] * m)).clip(lower=0)
                q['Extra_Bonus_Value'] = np.floor(q['Extra_Achieved'] / 2) * incremental_bonus
            elif campaign_name == "Collections":
                if targets["coll_amt"] > 0: q = q[q['Amount_Collected'] >= (targets["coll_amt"] * m)]
                if targets["dd7"] > 0: q = q[q['DD_Plus_7_Pct'] >= targets["dd7"]]
                if targets["otc"] > 0: q = q[q['OTC_Pct'] >= targets["otc"]]
                q['Extra_Bonus_Value'] = 0.0
            elif campaign_name == "Disbursements":
                q = q[q['Disbursements'] >= targets["disb"]]
                q['Extra_Achieved'] = (q['Disbursements'] - targets["disb"]).clip(lower=0)
                q['Extra_Bonus_Value'] = np.floor(q['Extra_Achieved'] / disb_inc_rate) * disbursement_bonus_step

            q['Base_Bonus'] = base_bonus
            q['Staff_Payout_Amount'] = q['Base_Bonus'] + q.get('Extra_Bonus_Value', 0)

            # Map Staff Details
            if eval_level == "Pairs (LO & CO)":
                q['Role'] = [['Loan Officer', 'Collections Officer'] for _ in range(len(q))]
                staff_df = q.explode('Role')
                merge_keys = ['Branch', 'Pair_ID', 'Role']
            else:
                role_name = eval_level.rstrip('s') # Convert Managers -> Manager
                staff_df = q.assign(Role=role_name)
                merge_keys = [group_key, 'Role']

            if staff_file:
                s_dir = pd.read_csv(staff_file, dtype={'Phone_Number': str, 'Pair_ID': str})
                staff_df = staff_df.merge(s_dir.drop_duplicates(merge_keys), on=merge_keys, how='left')

            # --- DISPLAY RESULTS ---
            if not staff_df.empty:
                st.divider()
                # Summary Metrics
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Payout Budget", f"${staff_df['Staff_Payout_Amount'].sum():,.2f}")
                m2.metric("Eligible Recipients", len(staff_df))
                m3.metric("Avg. Payout", f"${staff_df['Staff_Payout_Amount'].mean():,.2f}")

                st.dataframe(staff_df, use_container_width=True)
                
                csv = staff_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="⬇️ Download Payout Report",
                    data=csv,
                    file_name=f'UPIA_{campaign_name}_{eval_level}.csv',
                    mime='text/csv',
                    type="primary"
                )
            else:
                st.warning("⚠️ No staff members met the performance criteria for this selection.")

        except Exception as e:
            st.error(f"Critical Error processing files: {e}")