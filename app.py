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
    st.caption("v3.2 Final Edition")
    st.divider()

    selected_page = st.radio(
        "Select Module:", 
        ["📊 Dashboard", "🏗️ The Transformer", "📈 The Visualizer", "🧹 The Janitor", "🤖 AI Analyst"]
    )
    
    st.divider()
    
    with st.expander("⚙️ File Settings", expanded=True):
        has_header = st.checkbox("File has headers", value=True)
    
    with st.expander("🔑 AI Configuration"):
        try:
            if "GROQ_API_KEY" in st.secrets:
                api_key = st.secrets["GROQ_API_KEY"]
                st.success("✅ Key Loaded")
            else:
                api_key = st.text_input("Groq API Key", type="password")
        except:
            api_key = st.text_input("Groq API Key", type="password")

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
        
        # Color Logic
        dups = df.duplicated().sum()
        dup_color = "#ff4b4b" if dups > 0 else "inherit"
        missing = df.isnull().sum().sum()
        
        with c1: 
            st.markdown(f"<div class='metric-card'><div class='metric-value'>{len(df):,}</div><div class='metric-label'>Total Rows</div></div>", unsafe_allow_html=True)
        with c2: 
            st.markdown(f"<div class='metric-card'><div class='metric-value'>{len(df.columns)}</div><div class='metric-label'>Columns</div></div>", unsafe_allow_html=True)
        with c3: 
            st.markdown(f"<div class='metric-card'><div class='metric-value' style='color:{dup_color}'>{dups:,}</div><div class='metric-label'>Exact Duplicates</div></div>", unsafe_allow_html=True)
        with c4: 
            st.markdown(f"<div class='metric-card'><div class='metric-value'>{missing:,}</div><div class='metric-label'>Missing Values</div></div>", unsafe_allow_html=True)
        
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
            
            # Select Columns
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
                
                # --- A. CLEANING ---
                try:
                    df[date_col] = pd.to_datetime(df[date_col], errors='coerce').dt.date
                except: pass
                
                # Create clean ID column
                df['_clean_id'] = df[acct_col].astype(str).str.strip().str.lower()
                
                # --- B. FILTERING ---
                target_rows = df[df[date_col] == target_date]
                active_ids = target_rows['_clean_id'].unique()
                
                if show_history:
                    # Match using the CLEAN ID
                    filtered_df = df[df['_clean_id'].isin(active_ids)].copy()
                else:
                    filtered_df = target_rows.copy()

                if not filtered_df.empty:
                    # --- C. COUNTING ---
                    global_counts = df['_clean_id'].value_counts()
                    filtered_df['Duplicate_Count'] = filtered_df['_clean_id'].map(global_counts)

                    # --- D. SORT & DISPLAY ---
                    sorted_df = filtered_df.sort_values(by=['Duplicate_Count', acct_col], ascending=[False, True])
                    
                    def highlight(row):
                        if row['Duplicate_Count'] > 1:
                            return ['background-color: rgba(255, 0, 0, 0.2)'] * len(row)
                        return [''] * len(row)
                    
                    dups = len(sorted_df[sorted_df['Duplicate_Count'] > 1])
                    
                    if dups > 0: 
                        st.warning(f"🚨 Found {dups} Conflict Rows")
                    else: 
                        st.success("✅ No duplicates found")
                    
                    # Cleanup: Remove helper column
                    sorted_df = sorted_df.drop(columns=['_clean_id'])
                    
                    display_cols = final_cols if final_cols else [c for c in sorted_df.columns if c != 'Duplicate_Count']
                    if 'Duplicate_Count' not in display_cols: 
                        display_cols.insert(0, 'Duplicate_Count')
                        
                    st.dataframe(sorted_df[display_cols].style.apply(highlight, axis=1), use_container_width=True)
                    
                    # Download
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        sorted_df[display_cols].to_excel(writer, index=False)
                    st.download_button("📥 Download Excel", buffer.getvalue(), "Sorted_Report.xlsx")
                else:
                    st.error(f"No records found for {target_date}")

    # ==========================
    # 3. VISUALIZER
    # ==========================
    elif selected_page == "📈 The Visualizer":
        st.title("📈 Instant Analytics")
        c1, c2, c3 = st.columns(3)
        with c1: 
            chart_type = st.selectbox("Chart Type", ["Bar", "Line", "Scatter", "Pie"])
        with c2: 
            x_axis = st.selectbox("X Axis", df.columns)
        with c3: 
            num_cols = df.select_dtypes(include=['number']).columns
            y_axis = st.selectbox("Y Axis", num_cols) if len(num_cols) > 0 else None
            
        if y_axis:
            if chart_type == "Bar": fig = px.bar(df, x=x_axis, y=y_axis)
            elif chart_type == "Line": fig = px.line(df, x=x_axis, y=y_axis)
            elif chart_type == "Scatter": fig = px.scatter(df, x=x_axis, y=y_axis)
            elif chart_type == "Pie": fig = px.pie(df, names=x_axis, values=y_axis)
            st.plotly_chart(fig, use_container_width=True)

    # ==========================
    # 4. JANITOR
    # ==========================
    elif selected_page == "🧹 The Janitor":
        st.title("🧹 Data Hygiene")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🗑️ Remove Exact Duplicates"):
                st.session_state.df = df.drop_duplicates()
                st.success("Cleaned.")
                st.rerun()
        with c2:
            if st.button("🩸 Fill N/A values"):
                st.session_state.df = df.fillna("N/A")
                st.success("Filled N/A")
                st.rerun()
        st.dataframe(df.head())

    # ==========================
    # 5. AI ANALYST
    # ==========================
    elif selected_page == "🤖 AI Analyst":
        st.title("🤖 AI Data Analyst")
        st.markdown("Ask questions about your data in plain English.")
        
        if not api_key:
            st.warning("⚠️ Enter Groq API Key in Sidebar.")
        else:
            q = st.text_input("Ask a question:", placeholder="e.g. What is the most common Account ID?")
            if q:
                try:
                    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=api_key)
                    cols_str = ', '.join(df.columns)
                    rows_str = df.head().to_string(index=False)
                    prompt = f"Analyze this dataset:\nColumns: {cols_str}\nFirst 5 rows:\n{rows_str}\n\nQuestion: {q}\nAnswer concisely."
                    with st.spinner("Analyzing..."):
                        response = client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=[{"role": "user", "content": prompt}]
                        )
                        st.info(response.choices[0].message.content)
                except Exception as e: st.error(f"Error: {e}")

else:
    st.markdown("<br><h1 style='text-align:center'>👋 DataStudio Pro</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center'>Upload a file to begin.</p>", unsafe_allow_html=True)