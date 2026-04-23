import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. PAGE SETUP & CSS
# ==========================================
st.set_page_config(page_title="UPIA Incentive System", page_icon="🏢", layout="wide")

# --- HIDE STREAMLIT BRANDING (BUT KEEP SIDEBAR BUTTON) ---
hide_menu_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        /* This targets the top-right deployment decoration but leaves the sidebar toggle alone */
        .stAppDeployButton {display:none;}
        [data-testid="stHeader"] {background: rgba(0,0,0,0); height: 0rem;} 
        
        /* Prevent UI elements from printing */
        @media print {
            #MainMenu, .stSidebar, header { display: none !important; }
        }
        </style>
        """
st.markdown(hide_menu_style, unsafe_allow_html=True)

# ==========================================
# 2. LOGIN GATE SYSTEM
# ==========================================
def check_password():
    def password_entered():
        if (
            st.session_state["username"] in st.secrets["passwords"]
            and st.session_state["password"] == st.secrets["passwords"][st.session_state["username"]]
        ):
            st.session_state["password_correct"] = True
            st.session_state["active_user"] = st.session_state["username"]
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔒 System Login")
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", key="password")
        st.button("Login", on_click=password_entered)
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("😕 Username or password incorrect.")
    return False

if not check_password():
    st.stop()

# ==========================================
# 3. PAGE ROUTING & SIDEBAR
# ==========================================
if "current_page" not in st.session_state:
    st.session_state.current_page = "calculator"

st.sidebar.title("Configuration")

# Admin Toggle
if st.session_state.get("active_user") == "admin":
    st.sidebar.write("### 🛠️ Administration")
    if st.session_state.current_page == "calculator":
        if st.sidebar.button("⚙️ Open Admin Dashboard", use_container_width=True):
            st.session_state.current_page = "admin"
            st.rerun()
    else:
        if st.sidebar.button("⬅️ Back to Calculator", use_container_width=True):
            st.session_state.current_page = "calculator"
            st.rerun()
    st.sidebar.divider()

if st.session_state.current_page == "calculator":
    eval_level = st.sidebar.selectbox(
        "1. Select Evaluation Level",
        ["Pairs (LO & CO)", "Branch Managers", "Assistant Sector Managers", "Sector Managers"]
    )

    st.sidebar.write("### 2. Select Active Campaigns")
    active_campaigns = []
    if st.sidebar.checkbox("New Customers"): active_campaigns.append("New Customers")
    if st.sidebar.checkbox("Unique Customers"): active_campaigns.append("Unique Customers")
    if st.sidebar.checkbox("Active Customers"): active_campaigns.append("Active Customers")
    if st.sidebar.checkbox("Dormant Customers"): active_campaigns.append("Dormant Customers")
    if st.sidebar.checkbox("Collections"): active_campaigns.append("Collections")
    if st.sidebar.checkbox("Disbursements"): active_campaigns.append("Disbursements")

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

    # --- PAYOUT SETTINGS ---
    st.sidebar.write("### 💵 Payout Settings")
    base_bonus = st.sidebar.number_input("Base Bonus", value=3000.0, step=500.0)
    
    incremental_bonus = 0.0
    disbursement_bonus_step = 0.0
    cust_campaigns = ["New Customers", "Unique Customers", "Active Customers", "Dormant Customers"]
    
    if any(c in active_campaigns for c in cust_campaigns):
        incremental_bonus = st.sidebar.number_input("Extra Bonus (Per 2 Extra Customers)", value=200.0, step=100.0)
    if "Disbursements" in active_campaigns:
        disbursement_bonus_step = st.sidebar.number_input("Extra Bonus (Per 1% Extra)", value=200.0, step=50.0)

    # --- TARGET CUSTOMIZATION ---
    st.sidebar.divider()
    st.sidebar.write("### 🎯 Target Customization")
    
    new_cust_t = unique_cust_t = active_cust_t = dormant_cust_t = 0.0
    coll_amt_t = dd7_t = otc_t = disb_pct_t = 0.0

    if "New Customers" in active_campaigns:
        new_cust_t = st.sidebar.number_input("Base Min New Customers", value=6.0)
    if "Unique Customers" in active_campaigns:
        unique_cust_t = st.sidebar.number_input("Base Min Unique Customers", value=6.0)
    if "Active Customers" in active_campaigns:
        active_cust_t = st.sidebar.number_input("Base Min Active Customers", value=10.0)
    if "Dormant Customers" in active_campaigns:
        dormant_cust_t = st.sidebar.number_input("Base Min Dormant Customers", value=2.0)
    if "Collections" in active_campaigns:
        coll_amt_t = st.sidebar.number_input("Base Min Collection Amount", value=50000.0)
        dd7_t = st.sidebar.number_input("Min DD+7 (%)", value=80.0)
        otc_t = st.sidebar.number_input("Min OTC (%)", value=75.0)
    if "Disbursements" in active_campaigns:
        disb_pct_t = st.sidebar.number_input("Min Disbursement (%)", value=100.0)

# ==========================================
# 4. MAIN CONTENT
# ==========================================
if st.session_state.current_page == "admin":
    st.title("⚙️ User Management Dashboard")
    col1, col2 = st.columns(2)
    with col1:
        new_role = st.selectbox("User Role", ["Branch Manager", "Sector Manager", "HR Admin", "Finance Officer"])
        new_user = st.text_input("Username")
    with col2:
        st.write("") 
        st.write("") 
        new_pass = st.text_input("Password", type="password")
    
    if st.button("Generate Secure Access Code", type="primary"):
        if new_user and new_pass:
            st.success("✅ Code generated!")
            st.code(f'# {new_role}\n{new_user} = "{new_pass}"', language="toml")
        else:
            st.error("Fill out all fields.")

else:
    st.title("UPIA Incentive System 🏢")
    
    if not active_campaigns:
        st.info("👈 Please select at least one active campaign from the sidebar to begin.")
        st.stop()
        
    st.write(f"**Level:** {eval_level} | **Active Campaigns:** {', '.join(active_campaigns)}")

    c1, c2 = st.columns(2)
    with c1: perf_file = st.file_uploader("1. Upload Performance CSV", type=['csv'])
    with c2: staff_file = st.file_uploader("2. Upload Staff Directory CSV", type=['csv'])

    if perf_file:
        try:
            df = pd.read_csv(perf_file)
            
            # Sanitization
            num_cols = ['New_Customers', 'Unique_Customers', 'Active_Customers', 'Dormant_Customers', 'Amount_Collected', 'DD_Plus_7_Pct', 'OTC_Pct', 'Disbursements']
            for col in num_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace(r'[%$,]', '', regex=True), errors='coerce').fillna(0)
            
            org_keys = ['Pair_ID', 'Branch', 'Subsector', 'Sector']
            for k in org_keys:
                if k in df.columns: df[k] = df[k].astype(str).str.strip().str.title()

            # Aggregation logic
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

            # Filtering logic using dynamic mask (AND condition)
            q = eval_df.copy()
            mult = q['Target_Multiplier']
            mask = pd.Series([True] * len(q), index=q.index)
            
            if "New Customers" in active_campaigns:
                mask &= (q['New_Customers'] >= (new_cust_t * mult))
            if "Unique Customers" in active_campaigns:
                mask &= (q['Unique_Customers'] >= (unique_cust_t * mult))
            if "Active Customers" in active_campaigns:
                mask &= (q['Active_Customers'] >= (active_cust_t * mult))
            if "Dormant Customers" in active_campaigns:
                mask &= (q['Dormant_Customers'] >= (dormant_cust_t * mult))
            if "Collections" in active_campaigns:
                mask &= (q['Amount_Collected'] >= (coll_amt_t * mult)) & (q['DD_Plus_7_Pct'] >= dd7_t) & (q['OTC_Pct'] >= otc_t)
            if "Disbursements" in active_campaigns:
                mask &= (q['Disbursements'] >= disb_pct_t)

            q = q[mask]

            # Calculating cumulative extra rewards based on active campaigns
            q['Staff_Payout_Amount'] = base_bonus
            
            if "New Customers" in active_campaigns:
                extra = (q['New_Customers'] - (new_cust_t * mult)).clip(lower=0)
                q['Staff_Payout_Amount'] += np.floor(extra / 2) * incremental_bonus
            if "Unique Customers" in active_campaigns:
                extra = (q['Unique_Customers'] - (unique_cust_t * mult)).clip(lower=0)
                q['Staff_Payout_Amount'] += np.floor(extra / 2) * incremental_bonus
            if "Active Customers" in active_campaigns:
                extra = (q['Active_Customers'] - (active_cust_t * mult)).clip(lower=0)
                q['Staff_Payout_Amount'] += np.floor(extra / 2) * incremental_bonus
            if "Dormant Customers" in active_campaigns:
                extra = (q['Dormant_Customers'] - (dormant_cust_t * mult)).clip(lower=0)
                q['Staff_Payout_Amount'] += np.floor(extra / 2) * incremental_bonus
            if "Disbursements" in active_campaigns:
                extra = (q['Disbursements'] - disb_pct_t).clip(lower=0)
                q['Staff_Payout_Amount'] += np.floor(extra) * disbursement_bonus_step

            # Role Splitting & Directory Merging
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
                # Force Phone Number to string to keep leading zero
                s_dir = pd.read_csv(staff_file, dtype={'Phone_Number': str, 'Pair_ID': str})
                for col in org_keys + ['Role']:
                    if col in s_dir.columns: s_dir[col] = s_dir[col].astype(str).str.strip().str.title()
                # Use multi-key merge for total accuracy
                staff_df = staff_df.merge(s_dir.drop_duplicates(m_keys), on=m_keys, how='left')

            # Final View Preparation
            cols = ['Sector', 'Subsector', 'Branch', 'Pair_ID', 'Staff_Name', 'Phone_Number', 'Role', 'DD_Plus_7_Pct', 'OTC_Pct', 'Disbursements', 'Unit_Count', 'Target_Multiplier', 'Staff_Payout_Amount']
            available = [c for c in cols if c in staff_df.columns]
            staff_df = staff_df[available]

            # Format percentages for UI Display (leaves raw data alone for CSV export)
            display_df = staff_df.copy()
            pct_cols = ['DD_Plus_7_Pct', 'OTC_Pct', 'Disbursements']
            for col in pct_cols:
                if col in display_df.columns:
                    display_df[col] = display_df[col].map("{:.1f}%".format)

            st.success(f"🎉 Generated {len(staff_df)} payouts!")
            st.dataframe(display_df)
            
            # Export uses raw numeric values (staff_df) instead of formatted strings (display_df)
            csv = staff_df.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Download CSV", data=csv, file_name='hybrid_campaign_payouts.csv', mime='text/csv')

        except Exception as e:
            st.error(f"Error processing: {e}")