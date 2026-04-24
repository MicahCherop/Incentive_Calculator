import streamlit as st
import pandas as pd
import numpy as np

# 1. Page Setup
st.set_page_config(
    page_title="4G Capital UPIA Incentive System", 
    page_icon="🏢", 
    layout="wide",
    initial_sidebar_state="expanded" # This keeps it open when the page loads
)

# --- ULTIMATE CLEAN UI (KEEPS SIDEBAR TOGGLE VISIBLE) ---
hide_menu_style = """
        <style>
        /* Hide the top right hamburger menu */
        #MainMenu {visibility: hidden;}
        
        /* Hide the "Made with Streamlit" footer */
        footer {visibility: hidden;}
        
        /* Hide the top decoration bar */
        div[data-testid="stHeader"] {
            background-color: rgba(0,0,0,0);
            color: white;
        }

        /* Ensure the sidebar button remains visible and clickable */
        button[kind="header"] {
            visibility: visible !format;
            color: #31333F; /* Standard Streamlit dark gray for visibility */
        }
        
        /* Hide the 'Deploy' button and other header junk */
        div[data-testid="stToolbar"] {visibility: hidden;}
        </style>
        """
st.markdown(hide_menu_style, unsafe_allow_html=True)

# ==========================================
# PAGE ROUTING SETUP
# ==========================================
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

# ==========================================
# PAGE 1: ADMIN DASHBOARD
# ==========================================
if st.session_state.current_page == "admin":
    st.title("⚙️ User Management Dashboard")
    st.write("Create configurations for users to access the system (if security is re-enabled).")
    
    st.info("💡 **Instructions:** Generate the code block below, then paste it under `[passwords]` in your Streamlit Cloud Secrets.")
    
    st.write("### Create User Access Code")
    col1, col2 = st.columns(2)
    with col1:
        new_role = st.selectbox("User Role", ["Branch Manager", "Sector Manager", "HR Admin", "Finance Officer"])
        new_user = st.text_input("Username")
    with col2:
        st.write("") # Spacer
        st.write("") # Spacer
        new_pass = st.text_input("Password", type="password")
    
    if st.button("Generate Secure Access Code", type="primary"):
        if new_user and new_pass:
            st.success("✅ Code generated!")
            st.code(f'# {new_role}\n{new_user} = "{new_pass}"', language="toml")
        else:
            st.error("Please fill out both fields.")

# ==========================================
# PAGE 2: THE MAIN CALCULATOR APP
# ==========================================
else:
    st.title("4G Capital UPIA Incentive System 🏢")
    
    # 2. Sidebar - Calculator Configuration
    st.sidebar.title("Configuration")

    eval_level = st.sidebar.selectbox(
        "1. Select Evaluation Level",
        ["Pairs (LO & CO)", "Branch Managers", "Assistant Sector Managers", "Sector Managers"]
    )

    campaign_name = st.sidebar.selectbox(
        "2. Select Campaign", 
        ["New Customers", "Unique Customers", "Active Customers", "Dormant Customers", "Collections", "Disbursements"]
    )

    st.sidebar.divider() 

    # --- DYNAMIC CAPACITY SCALING ---
    scale_threshold = 1
    if eval_level != "Pairs (LO & CO)":
        st.sidebar.write("### ⚖️ Target Scaling Rules")
        if eval_level == "Branch Managers":
            st.sidebar.success("Targets multiply by the number of Pairs.")
        elif eval_level == "Assistant Sector Managers":
            scale_threshold = st.sidebar.number_input("Standard ASM Branch Count", value=4)
        elif eval_level == "Sector Managers":
            scale_threshold = st.sidebar.number_input("Standard Sector Branch Count", value=25)
        st.sidebar.divider()

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
    
    new_cust_t = unique_cust_t = active_cust_t = dormant_cust_t = 0.0
    coll_amt_t = dd7_t = otc_t = disb_pct_t = 0.0
    use_coll_amt = use_dd7 = use_otc = False

    if campaign_name == "New Customers":
        new_cust_t = st.sidebar.number_input("Base Min New Customers", value=6.0)
    elif campaign_name == "Unique Customers":
        unique_cust_t = st.sidebar.number_input("Base Min Unique Customers", value=6.0)
    elif campaign_name == "Active Customers":
        active_cust_t = st.sidebar.number_input("Base Min Active Customers", value=10.0)
    elif campaign_name == "Dormant Customers":
        dormant_cust_t = st.sidebar.number_input("Base Min Dormant Customers", value=2.0)
    elif campaign_name == "Collections":
        st.sidebar.info("Select metrics:")
        use_coll_amt = st.sidebar.checkbox("Apply Min Collection Amount", value=True)
        if use_coll_amt: coll_amt_t = st.sidebar.number_input("Base Min Amount", value=50000.0)
        use_dd7 = st.sidebar.checkbox("Apply Min DD+7 (%)", value=True)
        if use_dd7: dd7_t = st.sidebar.number_input("Min DD+7 (%)", value=80.0)
        use_otc = st.sidebar.checkbox("Apply Min OTC (%)", value=True)
        if use_otc: otc_t = st.sidebar.number_input("Min OTC (%)", value=75.0)
    elif campaign_name == "Disbursements":
        disb_pct_t = st.sidebar.number_input("Min Disbursement (%)", value=100.0)

    # 5. Main Screen
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
            
            org_keys = ['Pair_ID', 'Branch', 'Subsector', 'Sector']
            for k in org_keys:
                if k in df.columns: df[k] = df[k].astype(str).str.strip().str.title()

            eval_df = df.copy()
            eval_df['Target_Multiplier'] = 1.0
            eval_df['Unit_Count'] = 1
            group_key = None
            
            if eval_level == "Branch Managers":
                group_key = 'Branch'
                unit_counts = df.groupby('Branch')['Pair_ID'].nunique().reset_index(name='Unit_Count')
            elif eval_level == "Assistant Sector Managers":
                group_key = 'Subsector'
                unit_counts = df.groupby('Subsector')['Branch'].nunique().reset_index(name='Unit_Count')
            elif eval_level == "Sector Managers":
                group_key = 'Sector'
                unit_counts = df.groupby('Sector')['Branch'].nunique().reset_index(name='Unit_Count')

            if group_key:
                agg = {c: 'sum' for c in ['New_Customers', 'Unique_Customers', 'Active_Customers', 'Dormant_Customers', 'Amount_Collected'] if c in df.columns}
                agg.update({c: 'mean' for c in ['DD_Plus_7_Pct', 'OTC_Pct', 'Disbursements'] if c in df.columns})
                eval_df = df.groupby(group_key).agg(agg).reset_index()
                eval_df = eval_df.merge(unit_counts, on=group_key)
                
                if eval_level == "Branch Managers":
                    eval_df['Target_Multiplier'] = eval_df['Unit_Count'].astype(float)
                else:
                    eval_df['Target_Multiplier'] = np.where(eval_df['Unit_Count'] > scale_threshold, eval_df['Unit_Count'] / scale_threshold, 1.0)

            q = eval_df.copy()
            mult = q['Target_Multiplier']
            
            if campaign_name == "New Customers": q = q[q['New_Customers'] >= (new_cust_t * mult)]
            elif campaign_name == "Unique Customers": q = q[q['Unique_Customers'] >= (unique_cust_t * mult)]
            elif campaign_name == "Active Customers": q = q[q['Active_Customers'] >= (active_cust_t * mult)]
            elif campaign_name == "Dormant Customers": q = q[q['Dormant_Customers'] >= (dormant_cust_t * mult)]
            elif campaign_name == "Collections":
                if use_coll_amt: q = q[q['Amount_Collected'] >= (coll_amt_t * mult)]
                if use_dd7: q = q[q['DD_Plus_7_Pct'] >= dd7_t]
                if use_otc: q = q[q['OTC_Pct'] >= otc_t]
            elif campaign_name == "Disbursements": q = q[q['Disbursements'] >= disb_pct_t]

            extra_c = 0.0
            if campaign_name in ["New Customers", "Unique Customers", "Active Customers", "Dormant Customers"]:
                target_val = {"New Customers": new_cust_t, "Unique Customers": unique_cust_t, "Active Customers": active_cust_t, "Dormant Customers": dormant_cust_t}[campaign_name]
                col_name = campaign_name.replace(" ", "_")
                extra_c = (q[col_name] - (target_val * mult)).clip(lower=0)
            
            extra_d = (q['Disbursements'] - disb_pct_t).clip(lower=0) if campaign_name == "Disbursements" else 0.0

            q['Staff_Payout_Amount'] = base_bonus + (np.floor(extra_c / 2) * incremental_bonus) + (np.floor(extra_d / disb_inc_rate) * disbursement_bonus_step)

            if eval_level == "Pairs (LO & CO)":
                q['Role'] = [['Loan Officer', 'Collections Officer'] for _ in range(len(q))]
                staff_df = q.explode('Role')
                m_keys = ['Branch', 'Pair_ID', 'Role']
            elif eval_level == "Branch Managers":
                staff_df = q.assign(Role='Branch Manager')
                m_keys = ['Branch', 'Role']
            elif eval_level == "Assistant Sector Managers":
                staff_df = q.assign(Role='Assistant Sector Manager')
                m_keys = ['Subsector', 'Role']
            else:
                staff_df = q.assign(Role='Sector Manager')
                m_keys = ['Sector', 'Role']

            if staff_file:
                s_dir = pd.read_csv(staff_file, dtype={'Phone_Number': str, 'Pair_ID': str})
                for col in org_keys + ['Role']:
                    if col in s_dir.columns: s_dir[col] = s_dir[col].astype(str).str.strip().str.title()
                staff_df = staff_df.merge(s_dir.drop_duplicates(m_keys), on=m_keys, how='left')

            st.success(f"🎉 Generated {len(staff_df)} payouts!")
            st.dataframe(staff_df)
            csv = staff_df.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Download CSV", data=csv, file_name=f'{campaign_name}_payouts.csv', mime='text/csv')

        except Exception as e:
            st.error(f"Error: {e}")