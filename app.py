import streamlit as st
import pandas as pd
import numpy as np

# 1. Page Setup
st.set_page_config(page_title="4G Capital UPIA Incentive System", page_icon="🏢", layout="wide")

# --- HIDE STREAMLIT BRANDING ---
hide_menu_style = """
        <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
        """
st.markdown(hide_menu_style, unsafe_allow_html=True)

# --- 🔒 LOGIN GATE SYSTEM ---
def check_password():
    """Returns `True` if the user had a correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if (
            st.session_state["username"] in st.secrets["passwords"]
            and st.session_state["password"] == st.secrets["passwords"][st.session_state["username"]]
        ):
            st.session_state["password_correct"] = True
            st.session_state["active_user"] = st.session_state["username"]
            del st.session_state["password"]  # Don't store password in memory
        else:
            st.session_state["password_correct"] = False

    # If already logged in, return True
    if st.session_state.get("password_correct", False):
        return True

    # Show login form
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔒 System Login")
        st.write("Please log in to access the Incentive Payout System.")
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", key="password")
        st.button("Login", on_click=password_entered)
        
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("😕 Username or password incorrect.")
            
    return False

# Stop execution if not logged in
if not check_password():
    st.stop()

# ==========================================
# PAGE ROUTING SETUP
# ==========================================
if "current_page" not in st.session_state:
    st.session_state.current_page = "calculator"

# Admin Navigation (Only visible to admin)
if st.session_state.get("active_user") == "admin":
    st.sidebar.divider()
    st.sidebar.write("### 🛠️ Administration")
    if st.session_state.current_page == "calculator":
        if st.sidebar.button("⚙️ Open Admin Dashboard", use_container_width=True):
            st.session_state.current_page = "admin"
            st.rerun()
    else:
        if st.sidebar.button("⬅️ Back to Calculator", use_container_width=True):
            st.session_state.current_page = "calculator"
            st.rerun()

# ==========================================
# PAGE 1: ADMIN DASHBOARD
# ==========================================
if st.session_state.current_page == "admin":
    st.title("⚙️ User Management Dashboard")
    st.write("Create configurations for new managers to access the system.")
    
    st.info("💡 **Instructions:** Generate the code block below, then paste it under `[passwords]` in your Streamlit Cloud Secrets.")
    
    st.write("### Create New User Access")
    col1, col2 = st.columns(2)
    with col1:
        new_role = st.selectbox("User Role", ["Branch Manager", "Sector Manager", "HR Admin", "Finance Officer"])
        new_user = st.text_input("Username", placeholder="e.g., jsmith")
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
elif st.session_state.current_page == "calculator":
    st.title("4G Capital UPIA Incentive System 🏢")
    st.write("Generate accurate payroll for Pairs, Branch Managers, ASMs, and Sector Managers.")

    # 2. Sidebar - Campaign & Level Selection
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

    # 3. Sidebar - Bonus Payout Settings
    st.sidebar.write("### 💵 Payout Settings")
    base_bonus = st.sidebar.number_input("Base Bonus", value=3000.0, step=500.0)

    incremental_bonus = 0.0
    disbursement_incremental_bonus = 0.0

    if campaign_name in ["New Customers", "Unique Customers", "Active Customers", "Dormant Customers"]:
        incremental_bonus = st.sidebar.number_input("Extra Bonus (Per 2 Extra Customers)", value=200.0, step=100.0)
    elif campaign_name == "Disbursements":
        disbursement_incremental_bonus = st.sidebar.number_input("Extra Bonus (Per 1% Extra Disbursement)", value=200.0, step=50.0)

    st.sidebar.divider()

    # 4. Sidebar - Customizable Targets
    st.sidebar.write("### 🎯 Target Customization")
    
    use_new_cust = use_unique_cust = use_active_cust = use_dormant_cust = False
    use_dd7 = use_otc = use_collection = use_disbursement = False
    new_cust_target = unique_cust_target = active_cust_target = dormant_cust_target = 0.0
    dd7_target = otc_target = collection_target = disbursement_target = 0.0

    if campaign_name == "New Customers":
        use_new_cust = True
        new_cust_target = st.sidebar.number_input("Base Min New Customers", value=6.0)
    elif campaign_name == "Unique Customers":
        use_unique_cust = True
        unique_cust_target = st.sidebar.number_input("Base Min Unique Customers", value=6.0)
    elif campaign_name == "Active Customers":
        use_active_cust = True
        active_cust_target = st.sidebar.number_input("Base Min Active Customers", value=10.0)
    elif campaign_name == "Dormant Customers":
        use_dormant_cust = True
        dormant_cust_target = st.sidebar.number_input("Base Min Dormant Customers", value=2.0)
    elif campaign_name == "Collections":
        use_collection = True
        collection_target = st.sidebar.number_input("Base Min Collection Amount", value=50000.0)
        dd7_target = st.sidebar.number_input("Min DD+7 (%)", value=80.0)
        otc_target = st.sidebar.number_input("Min OTC (%)", value=75.0)
        use_dd7 = use_otc = True
    elif campaign_name == "Disbursements":
        use_disbursement = True
        disbursement_target = st.sidebar.number_input("Min Disbursement (%)", value=100.0)

    # 5. Main Screen - Dual File Uploaders
    st.write(f"**Calculating For:** {eval_level} | **Campaign:** {campaign_name}")

    col1, col2 = st.columns(2)
    with col1:
        perf_file = st.file_uploader("1. Upload Performance CSV", type=['csv'])
    with col2:
        staff_file = st.file_uploader("2. Upload Staff Directory CSV", type=['csv'])

    if perf_file is not None:
        try:
            df = pd.read_csv(perf_file)
            
            # --- DATA CLEANING ---
            sum_cols = ['New_Customers', 'Unique_Customers', 'Active_Customers', 'Dormant_Customers', 'Amount_Collected']
            mean_cols = ['DD_Plus_7_Pct', 'OTC_Pct', 'Disbursements']
            
            for col in sum_cols + mean_cols:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.replace('%', '', regex=False).str.replace(',', '', regex=False)
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            org_keys = ['Pair_ID', 'Branch', 'Subsector', 'Sector']
            for key in org_keys:
                if key in df.columns:
                    df[key] = df[key].astype(str).str.strip().str.title()
            
            # --- AGGREGATION ENGINE ---
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
                agg_dict = {col: 'sum' for col in sum_cols if col in df.columns}
                agg_dict.update({col: 'mean' for col in mean_cols if col in df.columns})
                eval_df = df.groupby(group_key).agg(agg_dict).reset_index()
                eval_df = eval_df.merge(unit_counts, on=group_key)
                
                if eval_level == "Branch Managers":
                    eval_df['Target_Multiplier'] = eval_df['Unit_Count'].astype(float)
                else:
                    eval_df['Target_Multiplier'] = np.where(eval_df['Unit_Count'] > scale_threshold, eval_df['Unit_Count'] / scale_threshold, 1.0)

            # 6. Apply Filtering & 7. Calculate Payouts
            qualified_df = eval_df.copy()
            
            if use_new_cust: qualified_df = qualified_df[qualified_df['New_Customers'] >= (new_cust_target * qualified_df['Target_Multiplier'])]
            if use_unique_cust: qualified_df = qualified_df[qualified_df['Unique_Customers'] >= (unique_cust_target * qualified_df['Target_Multiplier'])]
            if use_active_cust: qualified_df = qualified_df[qualified_df['Active_Customers'] >= (active_cust_target * qualified_df['Target_Multiplier'])]
            if use_dormant_cust: qualified_df = qualified_df[qualified_df['Dormant_Customers'] >= (dormant_cust_target * qualified_df['Target_Multiplier'])]
            if use_collection: qualified_df = qualified_df[qualified_df['Amount_Collected'] >= (collection_target * qualified_df['Target_Multiplier'])]
            if use_dd7: qualified_df = qualified_df[qualified_df['DD_Plus_7_Pct'] >= dd7_target]
            if use_otc: qualified_df = qualified_df[qualified_df['OTC_Pct'] >= otc_target]
            if use_disbursement: qualified_df = qualified_df[qualified_df['Disbursements'] >= disbursement_target]

            extra_c = pd.Series(0.0, index=qualified_df.index)
            if use_new_cust: extra_c += (qualified_df['New_Customers'] - (new_cust_target * qualified_df['Target_Multiplier'])).clip(lower=0)
            if use_unique_cust: extra_c += (qualified_df['Unique_Customers'] - (unique_cust_target * qualified_df['Target_Multiplier'])).clip(lower=0)
            if use_active_cust: extra_c += (qualified_df['Active_Customers'] - (active_cust_target * qualified_df['Target_Multiplier'])).clip(lower=0)
            if use_dormant_cust: extra_c += (qualified_df['Dormant_Customers'] - (dormant_cust_target * qualified_df['Target_Multiplier'])).clip(lower=0)
            
            extra_d = (qualified_df['Disbursements'] - disbursement_target).clip(lower=0) if use_disbursement else pd.Series(0.0, index=qualified_df.index)

            qualified_df['Staff_Payout_Amount'] = base_bonus + (np.floor(extra_c / 2) * incremental_bonus) + (np.floor(extra_d) * disbursement_incremental_bonus)

            # 8. Assign Roles & 9. Merge
            if eval_level == "Pairs (LO & CO)":
                qualified_df['Role'] = [['Loan Officer', 'Collections Officer'] for _ in range(len(qualified_df))]
                staff_df = qualified_df.explode('Role')
                merge_keys = ['Branch', 'Pair_ID', 'Role']
            elif eval_level == "Branch Managers":
                staff_df = qualified_df.assign(Role='Branch Manager')
                merge_keys = ['Branch', 'Role']
            elif eval_level == "Assistant Sector Managers":
                staff_df = qualified_df.assign(Role='Assistant Sector Manager')
                merge_keys = ['Subsector', 'Role']
            else:
                staff_df = qualified_df.assign(Role='Sector Manager')
                merge_keys = ['Sector', 'Role']

            if staff_file:
                staff_dir = pd.read_csv(staff_file, dtype=str)
                for k in org_keys + ['Role']:
                    if k in staff_dir.columns: staff_dir[k] = staff_dir[k].str.strip().str.title()
                staff_df = staff_df.merge(staff_dir.drop_duplicates(merge_keys), on=merge_keys, how='left')

            # 10. Display & 11. Download
            st.success(f"🎉 Generated {len(staff_df)} payouts!")
            st.dataframe(staff_df)
            csv = staff_df.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Download CSV", data=csv, file_name='payouts.csv', mime='text/csv')

        except Exception as e:
            st.error(f"Error: {e}")