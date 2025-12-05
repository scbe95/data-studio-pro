import streamlit as st
import pandas as pd
from openai import OpenAI

# --- 1. SETUP (Must be first) ---
st.set_page_config(page_title="DataStudio Pro", layout="wide")

# --- 2. TITLE & STATUS ---
st.title("⚡ DataStudio Pro v5.0")
st.write("---")

# --- 3. THE UPLOADER (Now in the main center area) ---
st.header("Step 1: Upload Your File")
uploaded_file = st.file_uploader("Drop your Excel or CSV file here", type=["xlsx", "xls", "csv", "txt"])

# --- 4. DATA LOADING LOGIC ---
if uploaded_file:
    try:
        # Load the file
        if uploaded_file.name.endswith(('.csv', '.txt')):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
            
        # Convert columns to string for safety
        df.columns = df.columns.astype(str)
        st.success(f"✅ Successfully loaded {len(df)} rows!")
        
        # --- 5. THE APP MODULES (Only show AFTER upload) ---
        st.write("---")
        
        # Sidebar Navigation
        with st.sidebar:
            st.header("Navigation")
            module = st.radio("Choose Tool:", ["📊 Dashboard", "🤖 AI Analyst"])
            
            st.divider()
            
            # API Key Check
            api_key = None
            if "GROQ_API_KEY" in st.secrets:
                api_key = st.secrets["GROQ_API_KEY"]
                st.success("🔑 AI Key Active")
            else:
                st.warning("⚠️ Secrets not found")

        # Module 1: Dashboard
        if module == "📊 Dashboard":
            st.subheader("Data Overview")
            st.dataframe(df.head(10), use_container_width=True)
            
            c1, c2 = st.columns(2)
            c1.metric("Total Rows", len(df))
            c1.metric("Total Columns", len(df.columns))

        # Module 2: AI Analyst
        elif module == "🤖 AI Analyst":
            st.subheader("🤖 Ask the AI")
            question = st.text_input("What do you want to know?")
            
            if question and api_key:
                client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=api_key)
                
                # Context
                preview = df.head().to_string()
                cols = ", ".join(df.columns)
                prompt = f"Data columns: {cols}\nPreview: {preview}\nQuestion: {question}\nAnswer in plain English, no code."
                
                with st.spinner("Thinking..."):
                    res = client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    st.info(res.choices[0].message.content)

    except Exception as e:
        st.error(f"❌ Error reading file: {e}")

else:
    # Landing Page Message
    st.info("👆 Waiting for file upload...")