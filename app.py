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

# --- 🔓 SIDEBAR TOGGLE VISIBLE & HIDE BRANDING ---
sidebar_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stAppDeployButton {display:none;}
    [data-testid="stHeader"] { background: rgba(0,0,0,0); } 
    [data-testid="stSidebar"] { min-width: 300px; max-width: 300px; }
    .block-container { padding-top: 2rem; }
    </style>
    """
st.markdown(sidebar_style, unsafe_allow_html=True)

if "current_page" not in st.session_state:
    st.session_state.current_page = "calculator"

# Navigation Sidebar
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
    
    st.sidebar.title("Configuration")
    eval_level = st.sidebar.selectbox("1. Select Evaluation Level", ["Pairs (LO & CO)", "Branch Managers", "Assistant Sector Managers", "Sector Managers"])
    campaign_name = st.sidebar.selectbox("2. Select Campaign", ["New Customers", "Unique Customers", "Active Customers", "Dormant Customers", "Collections", "Disbursements"])

    st.sidebar.divider() 
    scale_threshold = 1
    if eval_level != "Pairs (LO & CO)":
        if eval_level == "Assistant Sector Managers": scale_threshold = st.sidebar.number_input("Standard ASM Branch Count", value=4)
        elif eval_level == "Sector Managers": scale_threshold = st.sidebar.number_input("Standard Sector Branch Count", value=25)

    st.sidebar.write("### 💵 Payout Settings")
    base_bonus = st.sidebar.number_input("Base Bonus", value=3000.0, step=500.0)
    incremental_bonus = 0.0
    disbursement_bonus_step = 0.0
    disb_inc_rate = 1.0 

    if campaign_name in ["New Customers", "Unique Customers", "Active Customers", "Dormant Customers"]:
        incremental_bonus = st.sidebar.number_input("Extra Bonus (Per 2 Extra Customers)", value=200.0, step=100.0)
    elif campaign_name == "Disbursements":
        disb_inc_rate = st.sidebar.number_input("Reward for every X% extra", value=1.0, step=0.5)
        disbursement_bonus_step = st.sidebar.number_input(f"Extra Bonus (Per {disb_inc_rate}% Extra)", value=200.0, step=50.0)

    st.sidebar.divider()
    st.sidebar.write("### 🎯 Target Customization")
    new_cust_t = unique_cust_t = active_cust_t = dormant_cust_t = coll_amt_t = dd7_t = otc_t = disb_pct_t = 0.0
    use_coll_amt = use_dd7 = use_otc = False

    if campaign_name == "New Customers": new_cust_t = st.sidebar.number_input("Base Min New Customers", value=6.0)
    elif campaign_name == "Unique Customers": unique_cust_t = st.sidebar.number_input("Base Min Unique Customers", value=6.0)
    elif campaign_name == "Active Customers": active_cust_t = st.sidebar.number_input("Base Min Active Customers", value=10.0)
    elif campaign_name == "Dormant Customers": dormant_cust_t = st.sidebar.number_input("Base Min Dormant Customers", value=2.0)
    elif campaign_name == "Collections":
        use_coll_amt = st.sidebar.checkbox("Apply Min Collection Amount", value=True)
        if use_coll_amt: coll_amt_t = st.sidebar.number_input("Base Min Amount", value=50000.0)
        use_dd7 = st.sidebar.checkbox("Apply Min DD+7 (%)", value=True)
        if use_dd7: dd7_t = st.sidebar.number_input("Min DD+7 (%)", value=94.0)
        use_otc = st.sidebar.checkbox("Apply Min OTC (%)", value=True)
        if use_otc: otc_t = st.sidebar.number_input("Min OTC (%)", value=91.0)
    elif campaign_name == "Disbursements": disb_pct_t = st.sidebar.number_input("Min Disbursement (%)", value=100.0)

    st.write(f"**Level:** {eval_level} | **Campaign:** {campaign_name}")
    c1, c2 = st.columns(2)
    with c1: perf_file = st.file_uploader("1. Upload Performance CSV", type=['csv'])
    with c2: staff_file = st.file_uploader("2. Upload Staff Directory CSV", type=['csv'])

    if perf_file:
        try:
            df = pd.read_csv(perf_file)
            num_cols = ['New_Customers', 'Unique_Customers', 'Active_Customers', 'Dormant_Customers', 'Amount_Collected', 'DD_Plus_7_Pct', 'OTC_Pct', 'Disbursements']
            for col in num_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace(r'[%$,]', '', regex=True), errors='coerce').fillna(0)
            
            eval_df = df.copy()
            eval_df['Target_Multiplier'] = 1.0
            group_key = {'Branch Managers': 'Branch', 'Assistant Sector Managers': 'Subsector', 'Sector Managers': 'Sector'}.get(eval_level)
            
            if group_key:
                unit_counts = df.groupby(group_key)['Pair_ID' if eval_level == 'Branch Managers' else 'Branch'].nunique().reset_index(name='Unit_Count')
                agg = {c: 'sum' for c in ['New_Customers', 'Unique_Customers', 'Active_Customers', 'Dormant_Customers', 'Amount_Collected'] if c in df.columns}
                agg.update({c: 'mean' for c in ['DD_Plus_7_Pct', 'OTC_Pct', 'Disbursements'] if c in df.columns})
                eval_df = df.groupby(group_key).agg(agg).reset_index().merge(unit_counts, on=group_key)
                if eval_level == "Branch Managers": eval_df['Target_Multiplier'] = eval_df['Unit_Count'].astype(float)
                else: eval_df['Target_Multiplier'] = np.where(eval_df['Unit_Count'] > scale_threshold, eval_df['Unit_Count'] / scale_threshold, 1.0)

            q = eval_df.copy()
            mult = q.get('Target_Multiplier', 1.0)
            
            # Filter logic
            if campaign_name == "New Customers": q = q[q['New_Customers'] >= (new_cust_t * mult)]
            elif campaign_name == "Unique Customers": q = q[q['Unique_Customers'] >= (unique_cust_t * mult)]
            elif campaign_name == "Active Customers": q = q[q['Active_Customers'] >= (active_cust_t * mult)]
            elif campaign_name == "Dormant Customers": q = q[q['Dormant_Customers'] >= (dormant_cust_t * mult)]
            elif campaign_name == "Collections":
                if use_coll_amt: q = q[q['Amount_Collected'] >= (coll_amt_t * mult)]
                if use_dd7: q = q[q['DD_Plus_7_Pct'] >= dd7_t]
                if use_otc: q = q[q['OTC_Pct'] >= otc_t]
            elif campaign_name == "Disbursements": q = q[q['Disbursements'] >= disb_pct_t]

            # Payout logic with extra columns
            extra_val = 0.0
            if campaign_name in ["New Customers", "Unique Customers", "Active Customers", "Dormant Customers"]:
                target_val = {"New Customers": new_cust_t, "Unique Customers": unique_cust_t, "Active Customers": active_cust_t, "Dormant Customers": dormant_cust_t}[campaign_name]
                col_name = campaign_name.replace(" ", "_")
                extra_val = (q[col_name] - (target_val * mult)).clip(lower=0)
                q['Extra_Achieved'] = extra_val
                q['Extra_Bonus_Value'] = np.floor(extra_val / 2) * incremental_bonus
            elif campaign_name == "Disbursements":
                extra_val = (q['Disbursements'] - disb_pct_t).clip(lower=0)
                q['Extra_Achieved'] = extra_val
                q['Extra_Bonus_Value'] = np.floor(extra_val / disb_inc_rate) * disbursement_bonus_step
            else:
                q['Extra_Achieved'] = 0
                q['Extra_Bonus_Value'] = 0

            q['Base_Bonus'] = base_bonus
            q['Staff_Payout_Amount'] = q['Base_Bonus'] + q['Extra_Bonus_Value']

            # Merge with Directory
            if eval_level == "Pairs (LO & CO)":
                q['Role'] = [['Loan Officer', 'Collections Officer'] for _ in range(len(q))]
                staff_df = q.explode('Role')
                m_keys = ['Branch', 'Pair_ID', 'Role']
            else:
                staff_df = q.assign(Role=eval_level.rstrip('s'))
                m_keys = [{'Branch Managers': 'Branch', 'Assistant Sector Managers': 'Subsector', 'Sector Managers': 'Sector'}[eval_level], 'Role']

            if staff_file:
                s_dir = pd.read_csv(staff_file, dtype={'Phone_Number': str, 'Pair_ID': str})
                staff_df = staff_df.merge(s_dir.drop_duplicates(m_keys), on=m_keys, how='left')

            # Cleanup
            staff_df = staff_df.drop(columns=['Target_Multiplier', 'Unit_Count'], errors='ignore')
            
            st.success(f"🎉 Generated {len(staff_df)} payouts!")
            st.dataframe(staff_df)
            csv = staff_df.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Download CSV", data=csv, file_name=f'{campaign_name}_payouts.csv', mime='text/csv')

        except Exception as e:
            st.error(f"Error: {e}")