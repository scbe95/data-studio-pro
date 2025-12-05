import streamlit as st
import pandas as pd
import plotly.express as px
import io
from openai import OpenAI

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="DataStudio Pro", page_icon="⚡", layout="wide")

st.markdown("""
    <style>
    .metric-card {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 20px;
    }
    .metric-value { font-size: 2rem; font-weight: bold; }
    .metric-label { font-size: 0.9rem; opacity: 0.8; }
    div.stButton > button { width: 100%; border-radius: 6px; font-weight: 600; height: 45px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1256/1256628.png", width=50)
    st.title("DataStudio Pro")
    st.caption("v3.6 Insight Edition")
    st.divider()

    selected_page = st.radio(
        "Select Module:", 
        ["📊 Dashboard", "🏗️ The Transformer", "📈 The Visualizer", "🧹 The Janitor", "🤖 AI Analyst"]
    )
    
    st.divider()
    
    with st.expander("⚙️ File Settings", expanded=True):
        has_header = st.checkbox("File has headers", value=True)
    
    # --- SECURE KEY LOADING ---
    api_key = None
    try:
        if "GROQ_API_KEY" in st.secrets:
            api_key = st.secrets["GROQ_API_KEY"]
            st.success("✅ Secure Key Loaded")
    except:
        st.warning("⚠️ No secrets found. Check .streamlit/secrets.toml")

    st.divider()
    uploaded_file = st.file_uploader("Upload Dataset", type=["xlsx", "xls", "csv", "txt"])

# --- 3. DATA LOADER ---
if 'df' not in st.session_state:
    st.session_state.df = None

if uploaded_file:
    try:
        header_opt = 0 if has_header else None
        if uploaded_file.name.endswith(('.csv', '.txt')):
            st.session_state.df = pd.read_csv(uploaded_file, sep=None, engine='python', header=header_opt)
        else:
            st.session_state.df = pd.read_excel(uploaded_file, header=header_opt)
    except Exception as e:
        st.error(f"❌ Error loading file: {e}")

# --- 4. MAIN APP LOGIC ---
if st.session_state.df is not None:
    df = st.session_state.df
    # 1. Force all headers to be strings
    df.columns = df.columns.astype(str)
    
    # ==========================
    # 1. DASHBOARD
    # ==========================
    if selected_page == "📊 Dashboard":
        st.title("📊 Data Overview")
        st.markdown("### Executive Summary")
        c1, c2, c3, c4 = st.columns(4)
        
        dups = df.duplicated().sum()
        dup_color = "#ff4b4b" if dups > 0 else "inherit"
        missing = df.isnull().sum().sum()
        
        with c1: st.markdown(f"<div class='metric-card'><div class='metric-value'>{len(df):,}</div><div class='metric-label'>Total Rows</div></div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='metric-card'><div class='metric-value'>{len(df.columns)}</div><div class='metric-label'>Columns</div></div>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div class='metric-card'><div class='metric-value' style='color:{dup_color}'>{dups:,}</div><div class='metric-label'>Exact Duplicates</div></div>", unsafe_allow_html=True)
        with c4: st.markdown(f"<div class='metric-card'><div class='metric-value'>{missing:,}</div><div class='metric-label'>Missing Values</div></div>", unsafe_allow_html=True)
        
        st.subheader("📄 Data Preview")
        st.dataframe(df.head(10), use_container_width=True)

    # ==========================
    # 2. THE TRANSFORMER
    # ==========================
    elif selected_page == "🏗️ The Transformer":
        st.title("🏗️ Report Fixer")
        
        col_config, col_preview = st.columns([1, 2])
        
        with col_config:
            st.markdown("### Settings")
            all_cols = df.columns.tolist()
            
            default_date = next((i for i, c in enumerate(all_cols) if 'date' in c.lower()), 0)
            date_col = st.selectbox("📅 Date Column", all_cols, index=default_date)
            
            default_acct = next((i for i, c in enumerate(all_cols) if 'account' in c.lower() or 'id' in c.lower()), 0)
            acct_col = st.selectbox("🆔 Account ID Column", all_cols, index=default_acct)
            
            target_date = st.date_input("🎯 Target Date")
            
            st.divider()
            show_history = st.checkbox("Show duplicate rows from other dates?", value=True)
            final_cols = st.multiselect("📑 Final Column Order", all_cols, default=all_cols)
            
            if st.button("🚀 Process Report", type="primary"):
                st.session_state.run_transform = True

        with col_preview:
            if st.session_state.get('run_transform'):
                st.markdown("### Results")
                try:
                    df[date_col] = pd.to_datetime(df[date_col], errors='coerce').dt.date
                except: pass
                
                df['_clean_id'] = df[acct_col].astype(str).str.strip().str.lower()
                target_rows = df[df[date_col] == target_date]
                active_ids = target_rows['_clean_id'].unique()
                
                if show_history:
                    filtered_df = df[df['_clean_id'].isin(active_ids)].copy()
                else:
                    filtered_df = target_rows.copy()

                if not filtered_df.empty:
                    global_counts