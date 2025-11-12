import streamlit as st
import pandas as pd
import os
import base64
import PyPDF2
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq

# ---------- SETUP ----------
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
POLICY_DIR = "policies"
os.makedirs(POLICY_DIR, exist_ok=True)
QUERY_FILE = "queries.csv"
if not os.path.exists(QUERY_FILE):
    pd.DataFrame(columns=["timestamp", "context", "question", "answer"]).to_csv(QUERY_FILE, index=False)

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="Policy Insights Dashboard", page_icon="💼", layout="wide")

# ---------- THEME / STYLING ----------
st.markdown("""
<style>
body {
    background: linear-gradient(135deg, #eef2f3 0%, #8e9eab 100%);
}
.chat-bubble-user {
    background-color: #2E8B57; color: white; padding: 10px; border-radius: 10px; margin: 5px 0;
}
.chat-bubble-bot {
    background-color: #f0f2f6; color: black; padding: 10px; border-radius: 10px; margin: 5px 0;
    border-left: 4px solid #6C63FF;
}
.card {
    background: white; padding: 25px; border-radius: 15px;
    box-shadow: 0px 2px 10px rgba(0,0,0,0.1);
    margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)

# ---------- HELPER FUNCTIONS ----------
def ask_ai(prompt):
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a professional HR policy assistant that helps employees clearly understand company policies."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Error: {e}"

def save_query(context, question, answer):
    df = pd.read_csv(QUERY_FILE)
    new_row = pd.DataFrame([[datetime.now(), context, question, answer]], columns=["timestamp", "context", "question", "answer"])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(QUERY_FILE, index=False)

# ---------- SIDEBAR ----------
st.sidebar.title("💼 Policy Insights Dashboard")
st.sidebar.caption("Your company policy companion")
page = st.sidebar.radio("Navigate:", ["📚 All Policies", "📤 Upload or Choose & Ask", "💬 Ask Policy AI", "📊 My Analytics", "❓ My FAQs", "⚙️ Settings"])

# ---------- TABS ----------
if page == "📚 All Policies":
    st.title("📚 Company Policy Library")
    st.markdown("Browse or download official company policies.")

    files = [f for f in os.listdir(POLICY_DIR) if f.endswith(".pdf")]
    if not files:
        st.info("No policies available yet. Please upload via 'Upload or Choose & Ask'.")
    else:
        for file in files:
            path = os.path.join(POLICY_DIR, file)
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
                st.markdown(f"<div class='card'><b>📄 {file.replace('_',' ').title()}</b><br>"
                            f"<a href='data:application/octet-stream;base64,{b64}' download='{file}'>📥 Download</a></div>",
                            unsafe_allow_html=True)

elif page == "📤 Upload or Choose & Ask":
    st.title("📤 Upload or Choose Policy")
    st.markdown("Upload a new policy PDF or pick one from existing ones, then chat with the AI assistant about that document.")

    col1, col2 = st.columns(2)
    with col1:
        uploaded = st.file_uploader("Upload Policy PDF", type=["pdf"])
        if uploaded:
            save_path = os.path.join(POLICY_DIR, uploaded.name)
            with open(save_path, "wb") as f:
                f.write(uploaded.getbuffer())
            st.success(f"✅ Uploaded '{uploaded.name}'")

    with col2:
        files = [f for f in os.listdir(POLICY_DIR) if f.endswith(".pdf")]
        selected = st.selectbox("Or Choose Existing Policy", files if files else ["No files yet"])

    chosen_file = uploaded.name if uploaded else (selected if selected != "No files yet" else None)
    if chosen_file:
        with open(os.path.join(POLICY_DIR, chosen_file), "rb") as f:
            reader = PyPDF2.PdfReader(f)
            text = "\n".join(p.extract_text() for p in reader.pages if p.extract_text())

        st.markdown("### 💬 Chat with AI about this Policy")
        user_q = st.text_input("Ask something about this policy:")
        if st.button("Ask AI"):
            if user_q.strip():
                with st.spinner("Reading policy and generating answer..."):
                    answer = ask_ai(f"Policy: {chosen_file}\n\nContent:\n{text[:5000]}\n\nQuestion:\n{user_q}")
                    st.markdown(f"<div class='chat-bubble-user'><b>You:</b> {user_q}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='chat-bubble-bot'><b>AI:</b> {answer}</div>", unsafe_allow_html=True)
                    save_query(chosen_file, user_q, answer)
            else:
                st.warning("Please enter a question.")

elif page == "💬 Ask Policy AI":
    st.title("💬 Ask Policy AI (General Assistant)")
    st.markdown("Ask anything about company policies or HR practices — the AI will respond based on general guidelines.")
    question = st.text_area("Type your question:")
    if st.button("Ask"):
        if question.strip():
            with st.spinner("Thinking..."):
                answer = ask_ai(f"Employee Question: {question}")
                st.markdown(f"<div class='chat-bubble-user'><b>You:</b> {question}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='chat-bubble-bot'><b>AI:</b> {answer}</div>", unsafe_allow_html=True)
                save_query("General", question, answer)
        else:
            st.warning("Please enter a question.")

elif page == "📊 My Analytics":
    st.title("📊 My Analytics")
    df = pd.read_csv(QUERY_FILE)
    if df.empty:
        st.info("You haven’t asked any questions yet.")
    else:
        st.metric("Total Questions", len(df))
        st.metric("Unique Policies", df['context'].nunique())
        st.dataframe(df.sort_values("timestamp", ascending=False).head(10))

elif page == "❓ My FAQs":
    st.title("❓ Common Employee FAQs")
    df = pd.read_csv(QUERY_FILE)
    if df.empty:
        st.info("No data yet — start asking questions!")
    else:
        questions = "\n".join(df["question"].tolist())
        with st.spinner("Generating FAQs..."):
            faqs = ask_ai(f"From these employee questions, create a list of 5 common Q&A FAQs:\n{questions}")
        st.markdown(f"<div class='card'>{faqs}</div>", unsafe_allow_html=True)

elif page == "⚙️ Settings":
    st.title("⚙️ Settings & Appearance")
    st.write("Personalize your dashboard theme.")
    theme = st.selectbox("Choose Theme", ["Light", "Dark", "Corporate Blue"])
    if theme == "Dark":
        st.markdown("<style>body { background-color: #121212; color: #f5f5f5; }</style>", unsafe_allow_html=True)
    elif theme == "Corporate Blue":
        st.markdown("<style>body { background-color: #e6ebff; }</style>", unsafe_allow_html=True)
    st.success(f"Theme applied: {theme}")