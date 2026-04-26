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
    [data-testid="stSidebar"] { min-width: 320px; }
    .block-container { padding-top: 2rem; }
    
    /* Center the button vertically with the dropdown */
    div[data-testid="stColumn"] > div {
        display: flex;
        align-items: flex-end;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. Session State Initialization
if "levels" not in st.session_state:
    st.session_state.levels = {
        "Pairs (LO & CO)": {"group_key": None, "unit_name": "Pair"},
        "Branch Managers": {"group_key": "Branch", "unit_name": "Pair_ID"},
        "Assistant Sector Managers": {"group_key": "Subsector", "unit_name": "Branch"},
        "Sector Managers": {"group_key": "Sector", "unit_name": "Branch"}
    }

if "campaign_configs" not in st.session_state:
    all_lvls = list(st.session_state.levels.keys())
    st.session_state.campaign_configs = {
        "New Customers": {"metrics": ["New_Customers"], "applies_to": all_lvls},
        "Collections": {"metrics": ["Amount_Collected", "OTC_Pct", "DD_Plus_7_Pct", "Overall_Collection_Pct"], "applies_to": all_lvls},
        "Disbursements": {"metrics": ["Disb_Actual"], "applies_to": ["Pairs (LO & CO)", "Branch Managers"]}
    }

if "current_page" not in st.session_state:
    st.session_state.current_page = "calculator"

# --- 🛠️ DIALOGS ---
@st.dialog("Confirm Deletion")
def confirm_delete_dialog(campaign_name):
    st.warning(f"Are you sure you want to delete **{campaign_name}**?")
    if st.button("Yes, Delete", type="primary", use_container_width=True):
        del st.session_state.campaign_configs[campaign_name]
        st.toast(f"✅ Deleted {campaign_name}")
        st.rerun()

# 3. Helper Functions
def clean_numeric(series):
    return pd.to_numeric(
        series.astype(str).replace(r'[^-0-9.]', '', regex=True), 
        errors='coerce'
    ).fillna(0)

# 4. Navigation
st.sidebar.title("Navigation")
if st.session_state.current_page == "calculator":
    if st.sidebar.button("⚙️ System Configuration", use_container_width=True):
        st.session_state.current_page = "admin"
        st.rerun()
else:
    if st.sidebar.button("⬅️ Back to Calculator", use_container_width=True):
        st.session_state.current_page = "calculator"
        st.rerun()

# --- ⚙️ CONFIGURATION PAGE ---
if st.session_state.current_page == "admin":
    st.title("⚙️ System Configuration")
    
    col_l, col_r = st.columns(2)
    
    with col_l:
        st.subheader("🛠️ 1. Manage Levels")
        with st.form("add_level_form", clear_on_submit=True):
            lvl_name = st.text_input("Level Name")
            lvl_group = st.text_input("Group Column")
            lvl_unit = st.text_input("Unit Column")
            if st.form_submit_button("Add Level"):
                if lvl_name:
                    st.session_state.levels[lvl_name] = {"group_key": lvl_group if lvl_group else None, "unit_name": lvl_unit}
                    st.toast("✅ Level Added")
                    st.rerun()

    with col_r:
        st.subheader("🚀 2. Create Campaigns")
        with st.form("add_campaign_form", clear_on_submit=True):
            camp_name = st.text_input("Campaign Name")
            m_list = ["New_Customers", "Unique_Customers", "Active_Customers", "Active_No_Loans", "Dormant_Customers", "Amount_Collected", "OTC_Pct", "DD_Plus_7_Pct", "Overall_Collection_Pct", "Disb_Actual"]
            selected_metrics = [m for m in m_list if st.checkbox(m, key=f"c_{m}")]
            selected_lvls = [l for l in st.session_state.levels.keys() if st.checkbox(l, key=f"v_{l}")]
            if st.form_submit_button("Save Campaign"):
                if camp_name and selected_metrics and selected_lvls:
                    st.session_state.campaign_configs[camp_name] = {"metrics": selected_metrics, "applies_to": selected_lvls}
                    st.toast("✅ Campaign Linked")
                    st.rerun()

    st.divider()
    
    # --- 🗑️ MODIFIED DELETE SECTION (ONE ROW) ---
    st.subheader("🗑️ 3. Cleanup & Maintenance")
    # Using specific column ratios to ensure single-row fit
    del_col_select, del_col_btn = st.columns([3, 1]) 
    
    with del_col_select:
        campaign_to_delete = st.selectbox(
            "Select Campaign to Remove", 
            [""] + list(st.session_state.campaign_configs.keys()),
            label_visibility="collapsed" # Hides label to keep row slim
        )
    
    with del_col_btn:
        if st.button("🗑️ Delete Selected", type="secondary", use_container_width=True):
            if campaign_to_delete:
                confirm_delete_dialog(campaign_to_delete)
            else:
                st.warning("Select first!")

# --- 🏢 CALCULATOR PAGE ---
else:
    st.title("UPIA Incentive System 🏢")
    
    # Selection
    st.sidebar.subheader("🎯 Context")
    eval_level = st.sidebar.selectbox("Level", list(st.session_state.levels.keys()))
    available_campaigns = [name for name, cfg in st.session_state.campaign_configs.items() if eval_level in cfg.get("applies_to", [])]
    
    if not available_campaigns:
        st.sidebar.warning("No linked campaigns.")
        st.stop()
        
    campaign_name = st.sidebar.selectbox("Campaign", available_campaigns)

    # Multiplier
    scale_threshold = 1
    if eval_level == "Assistant Sector Managers": 
        scale_threshold = st.sidebar.number_input("Standard ASM Branches", value=4)
    elif eval_level == "Sector Managers": 
        scale_threshold = st.sidebar.number_input("Standard Sector Branches", value=25)

    # Payout
    st.sidebar.divider()
    st.sidebar.subheader("💵 Payout")
    base_bonus = st.sidebar.number_input("Base (kes)", value=3000.0)
    enable_extra = st.sidebar.checkbox("Extra Pay", value=True)
    bonus_step_count, bonus_step_amount = 2.0, 200.0

    if enable_extra:
        c1, c2 = st.sidebar.columns(2)
        with c1: bonus_step_count = st.number_input("Per Qty/%", value=2.0)
        with c2: bonus_step_amount = st.number_input("Extra (kes)", value=200.0)

    # Targets
    st.sidebar.divider()
    active_metrics = st.session_state.campaign_configs[campaign_name]["metrics"]
    targets, active_filters = {}, []

    for metric in active_metrics:
        if st.sidebar.checkbox(f"Apply {metric}", value=True):
            val = 90.0 if "Pct" in metric or "Actual" in metric else 6.0
            targets[metric] = st.sidebar.number_input(f"Min {metric}", value=val)
            active_filters.append(metric)

    # Processing
    c1, c2 = st.columns(2)
    perf_file = c1.file_uploader("Performance CSV", type=['csv'])
    staff_file = c2.file_uploader("Staff CSV", type=['csv'])

    if perf_file:
        try:
            df = pd.read_csv(perf_file)
            all_cols = [m for sub in st.session_state.campaign_configs.values() for m in sub["metrics"]] + ["Disb_Target"]
            for col in set(all_cols):
                if col in df.columns: df[col] = clean_numeric(df[col])
            
            lvl_cfg = st.session_state.levels[eval_level]
            group_key, unit_col = lvl_cfg["group_key"], lvl_cfg["unit_name"]
            
            if group_key and group_key in df.columns:
                unit_counts = df.groupby(group_key)[unit_col].nunique().reset_index(name='Unit_Count')
                agg_dict = {m: ('mean' if ("Pct" in m or "Actual" in m) else 'sum') for m in active_filters if m in df.columns}
                if "Disb_Target" in df.columns: agg_dict["Disb_Target"] = "sum"
                eval_df = df.groupby(group_key).agg(agg_dict).reset_index().merge(unit_counts, on=group_key)
                eval_df['Multiplier'] = eval_df['Unit_Count'].astype(float) if eval_level == "Branch Managers" else np.where(eval_df['Unit_Count'] > scale_threshold, eval_df['Unit_Count'] / scale_threshold, 1.0)
            else:
                eval_df = df.copy()
                eval_df['Multiplier'] = 1.0

            q = eval_df.copy()
            for f in active_filters:
                if f == "Disb_Actual" and "Disb_Target" in q.columns:
                    q['Disb_Achievement_Pct'] = (q['Disb_Actual'] / q['Disb_Target'] * 100).fillna(0)
                    q = q[q['Disb_Achievement_Pct'] >= targets[f]]
                elif "Pct" in f or "Actual" in f:
                    q = q[q[f] >= targets[f]]
                else:
                    q = q[q[f] >= (targets[f] * q['Multiplier'])]

            q['Base_Bonus'] = base_bonus
            q['Extra_Bonus'] = 0.0
            if enable_extra and not q.empty and active_filters:
                primary = active_filters[0]
                achieved = q['Disb_Achievement_Pct'] if primary == "Disb_Actual" and "Disb_Achievement_Pct" in q.columns else q[primary]
                t_val = targets[primary] if ("Pct" in primary or "Actual" in primary) else (targets[primary] * q['Multiplier'])
                q['Extra_Bonus'] = np.floor((achieved - t_val).clip(lower=0) / bonus_step_count) * bonus_step_amount

            q['Total_Payout'] = q['Base_Bonus'] + q['Extra_Bonus']

            if staff_file:
                s_dir = pd.read_csv(staff_file, dtype={'Pair_ID': str})
                m_key = group_key if group_key else "Pair_ID"
                q = q.merge(s_dir, on=m_key, how='left')

            if not q.empty:
                st.subheader(f"Results: {campaign_name}")
                st.dataframe(q, use_container_width=True)
                st.download_button("Download CSV", q.to_csv(index=False), "Report.csv", "text/csv")
            else:
                st.warning("No qualifiers.")
        except Exception as e:
            st.error(f"Error: {e}")