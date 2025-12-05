import streamlit as st
import pandas as pd
import io
from openai import OpenAI

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="DataStudio Pro", layout="wide")

# --- 2. HEADER & UPLOADER (Always Visible) ---
st.title("⚡ DataStudio Pro v8.0")
st.markdown("### Step 1: Upload Data")

# The uploader is NOT inside any if-statement, so it MUST show up
uploaded_file = st.file_uploader("Drop your file here:", type=["xlsx", "xls", "csv", "txt"])

# --- 3. MAIN APP ---
if uploaded_file is None:
    st.info("👆 Waiting for file... (If you see this, the app is working!)")
    st.stop()  # Stop code here until file is uploaded

# --- 4. DATA LOADING (Only happens if file exists) ---
try:
    if uploaded_file.name.endswith(('.csv', '.txt')):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    df.columns = df.columns.astype(str)
    st.success(f"✅ Loaded {len(df)} rows.")

except Exception as e:
    st.error(f"❌ File Error: {e}")
    st.stop()

# --- 5. SIDEBAR TOOLS ---
with st.sidebar:
    st.header("Tools")
    module = st.radio("Select Tool:", ["🕵️ Duplicate Hunter (Hybrid AI)", "📊 Dashboard"])
    st.divider()
    
    # Check for Secret Key
    api_key = None
    if "GROQ_API_KEY" in st.secrets:
        api_key = st.secrets["GROQ_API_KEY"]
        st.success("🔑 AI Connected")
    else:
        st.warning("⚠️ Secrets Missing")

# --- 6. TOOL: DUPLICATE HUNTER (Your Request) ---
if module == "🕵️ Duplicate Hunter (Hybrid AI)":
    st.header("🕵️ Hybrid Duplicate Hunter")
    st.markdown("**Logic:** Python finds the sort. AI explains the result.")
    
    # Inputs
    c1, c2 = st.columns(2)
    all_cols = df.columns.tolist()
    
    # Auto-selectors
    date_idx = next((i for i, c in enumerate(all_cols) if 'date' in c.lower()), 0)
    id_idx = next((i for i, c in enumerate(all_cols) if 'id' in c.lower() or 'account' in c.lower()), 0)
    
    date_col = c1.selectbox("Date Column", all_cols, index=date_idx)
    id_col = c2.selectbox("Account ID Column", all_cols, index=id_idx)
    target_date_input = st.date_input("Target List Date")
    
    if st.button("🚀 Find & Analyze"):
        # PYTHON SORTING (The Muscle)
        df['_clean_id'] = df[id_col].astype(str).str.strip().str.lower()
        
        # Date fix
        try:
            df[date_col] = pd.to_datetime(df[date_col]).dt.date
        except:
            df[date_col] = df[date_col].astype(str)

        # Logic: Find IDs on target date -> Find them in history -> Count > 1
        target_rows = df[df[date_col] == target_date_input]
        target_ids = target_rows['_clean_id'].unique()
        
        if len(target_ids) == 0:
            st.warning(f"No records found on {target_date_input}")
        else:
            history = df[df['_clean_id'].isin(target_ids)].copy()
            counts = history['_clean_id'].value_counts()
            history['Count'] = history['_clean_id'].map(counts)
            
            # The Filter
            final_dups = history[history['Count'] > 1]
            
            if final_dups.empty:
                st.success("✅ Clean! No duplicates found.")
            else:
                st.warning(f"🚨 Found {len(final_dups)} matches!")
                
                # Sort for easier reading
                final_dups = final_dups.sort_values(by=[id_col, date_col])
                display_df = final_dups.drop(columns=['_clean_id', 'Count'])
                
                st.dataframe(display_df, use_container_width=True)
                
                # Download
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    display_df.to_excel(writer, index=False)
                st.download_button("📥 Download Excel", buffer.getvalue(), "Sorted_Duplicates.xlsx")
                
                # AI ANALYSIS (The Brain)
                st.write("---")
                if api_key:
                    st.subheader("🤖 AI Insight")
                    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=api_key)
                    
                    # Feed the data to AI
                    context = display_df.head(15).to_string()
                    prompt = f"""
                    Review these duplicate accounts found across different dates.
                    
                    DATA:
                    {context}
                    
                    TASK:
                    1. Answer in plain English (No code).
                    2. Summarize where the duplicates are coming from (e.g. "Most match the Jan 1st list").
                    3. Are there any weird patterns?
                    """
                    
                    with st.spinner("Analyzing patterns..."):
                        res = client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=[{"role": "user", "content": prompt}]
                        )
                        st.info(res.choices[0].message.content)

# --- 7. TOOL: DASHBOARD ---
elif module == "📊 Dashboard":
    st.subheader("Quick Stats")
    st.metric("Total Rows", len(df))
    st.dataframe(df.head())