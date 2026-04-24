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
            bonus_step_amount = st.number_input("Pay Extra (kes)", value=200.0, step=50.0)
    elif campaign_name == "Disbursements":
        col1, col2 = st.sidebar.columns(2)
        with col1:
            bonus_step_count = st.number_input("For every (X%)", value=1.0, min_value=0.1, step=0.5)
        with col2:
            bonus_step_amount = st.number_input("Pay Extra (kes)", value=200.0, step=50.0)

    st.sidebar.divider()
    st.sidebar.write("### 🎯 Target Customization")
    
    targets = {}
    active_filters = []

    if "Customers" in campaign_name:
        key = campaign_name.replace(" ", "_")
        targets[key] = st.sidebar.number_input(f"Base Min {campaign_name} Required", value=6.0)
        active_filters.append(key)
    
    elif campaign_name == "Collections":
        # Checkboxes for flexible criteria
        use_amt = st.sidebar.checkbox("Filter by Amount Collected", value=True)
        if use_amt:
            targets["Amount_Collected"] = st.sidebar.number_input("Min Amount", value=50000.0)
            active_filters.append("Amount_Collected")
        
        use_otc = st.sidebar.checkbox("Filter by OTC %", value=True)
        if use_otc:
            targets["OTC_Pct"] = st.sidebar.number_input("Min OTC (%)", value=91.0)
            active_filters.append("OTC_Pct")
            
        use_dd7 = st.sidebar.checkbox("Filter by DD+7 %", value=True)
        if use_dd7:
            targets["DD_Plus_7_Pct"] = st.sidebar.number_input("Min DD+7 (%)", value=94.0)
            active_filters.append("DD_Plus_7_Pct")

        use_overall = st.sidebar.checkbox("Filter by Overall Collection %", value=False)
        if use_overall:
            targets["Overall_Collection_Pct"] = st.sidebar.number_input("Min Overall Collection (%)", value=95.0)
            active_filters.append("Overall_Collection_Pct")
            
    elif campaign_name == "Disbursements":
        targets["disb_threshold"] = st.sidebar.number_input("Qualification Threshold (%)", value=100.0)
        active_filters.append("disb_threshold")

    # File Uploaders
    st.write(f"**Level:** {eval_level} | **Campaign:** {campaign_name}")
    c1, c2 = st.columns(2)
    with c1: perf_file = st.file_uploader("1. Upload Performance CSV", type=['csv'])
    with c2: staff_file = st.file_uploader("2. Upload Staff Directory CSV", type=['csv'])

    if perf_file:
        try:
            df = pd.read_csv(perf_file)
            # Added Overall_Collection_Pct to clean list
            num_cols = ['New_Customers', 'Unique_Customers', 'Active_Customers', 'Dormant_Customers', 
                        'Amount_Collected', 'DD_Plus_7_Pct', 'OTC_Pct', 'Overall_Collection_Pct', 
                        'Disb_Target', 'Disb_Actual']
            for col in num_cols:
                if col in df.columns:
                    df[col] = clean_numeric(df[col])
            
            group_key = LEVEL_CONFIG[eval_level]["group_key"]
            unit_col = LEVEL_CONFIG[eval_level]["unit_name"]
            
            if group_key:
                unit_counts = df.groupby(group_key)[unit_col].nunique().reset_index(name='Unit_Count')
                agg_dict = {c: 'sum' for c in ['New_Customers', 'Unique_Customers', 'Active_Customers', 'Dormant_Customers', 'Amount_Collected', 'Disb_Target', 'Disb_Actual'] if c in df.columns}
                # Added Overall_Collection_Pct to mean aggregation
                agg_dict.update({c: 'mean' for c in ['DD_Plus_7_Pct', 'OTC_Pct', 'Overall_Collection_Pct'] if c in df.columns})
                eval_df = df.groupby(group_key).agg(agg_dict).reset_index().merge(unit_counts, on=group_key)
                eval_df['Multiplier'] = eval_df['Unit_Count'].astype(float) if eval_level == "Branch Managers" else np.where(eval_df['Unit_Count'] > scale_threshold, eval_df['Unit_Count'] / scale_threshold, 1.0)
            else:
                eval_df = df.copy()
                eval_df['Multiplier'] = 1.0

            # --- Calculation Engine ---
            q = eval_df.copy()
            m = q['Multiplier']
            
            # Apply active filters dynamically
            for filter_key in active_filters:
                if filter_key == "Amount_Collected":
                    q = q[q[filter_key] >= (targets[filter_key] * m)]
                elif filter_key in ["OTC_Pct", "DD_Plus_7_Pct", "Overall_Collection_Pct"]:
                    q = q[q[filter_key] >= targets[filter_key]]
                elif "Customers" in campaign_name:
                    q = q[q[filter_key] >= (targets[filter_key] * m)]

            # Calculate Extra Bonuses
            if "Customers" in campaign_name:
                col = campaign_name.replace(" ", "_")
                q['Extra_Achieved'] = (q[col] - (targets[col] * m)).clip(lower=0)
                q['Extra_Bonus_Value'] = np.floor(q['Extra_Achieved'] / bonus_step_count) * bonus_step_amount
            elif campaign_name == "Disbursements":
                q['Disb_Achievement_Pct'] = (q['Disb_Actual'] / q['Disb_Target'] * 100).fillna(0)
                q = q[q['Disb_Achievement_Pct'] >= targets["disb_threshold"]]
                q['Pct_Above_Threshold'] = (q['Disb_Achievement_Pct'] - targets["disb_threshold"]).clip(lower=0)
                q['Extra_Bonus_Value'] = np.floor(q['Pct_Above_Threshold'] / bonus_step_count) * bonus_step_amount
            else:
                q['Extra_Bonus_Value'] = 0.0

            q['Base_Bonus'] = base_bonus
            q['Staff_Payout_Amount'] = q['Base_Bonus'] + q['Extra_Bonus_Value']

            # Staff Mapping
            if eval_level == "Pairs (LO & CO)":
                q['Role'] = [['Loan Officer', 'Collections Officer'] for _ in range(len(q))]
                staff_df = q.explode('Role')
                m_keys = ['Branch', 'Pair_ID', 'Role']
            else:
                staff_df = q.assign(Role=eval_level.rstrip('s'))
                m_keys = [group_key, 'Role']

            if staff_file:
                s_dir = pd.read_csv(staff_file, dtype={'Phone_Number': str, 'Pair_ID': str})
                staff_df = staff_df.merge(s_dir.drop_duplicates(m_keys), on=m_keys, how='left')

            # --- Final Display ---
            if not staff_df.empty:
                st.divider()
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Payout", f"kes {staff_df['Staff_Payout_Amount'].sum():,.2f}")
                m2.metric("Qualifying Staff", len(staff_df))
                m3.metric("Avg. Bonus", f"kes {staff_df['Staff_Payout_Amount'].mean():,.2f}")
                st.dataframe(staff_df, use_container_width=True)
                csv = staff_df.to_csv(index=False).encode('utf-8')
                st.download_button("⬇️ Download Final Report", data=csv, file_name=f'Collections_Report.csv', mime='text/csv', type="primary")
            else:
                st.warning("No staff members qualified with the selected criteria.")

        except Exception as e:
            st.error(f"Error: {e}")