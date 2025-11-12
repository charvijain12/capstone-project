import streamlit as st
import pandas as pd
import plotly.express as px
import os
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime

# Load API Key
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Initialize OpenRouter client
client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

# CSV storage
QUERY_FILE = "queries.csv"
if not os.path.exists(QUERY_FILE):
    pd.DataFrame(columns=["timestamp", "question", "answer"]).to_csv(QUERY_FILE, index=False)

st.set_page_config(page_title="Policy Insights AI Dashboard", layout="wide")

# --- Sidebar ---
st.sidebar.title("⚙️ Dashboard Navigation")
page = st.sidebar.radio("Choose a tab:", ["💬 Chat & Upload", "📊 Analytics", "📞 Contacts"])

# --- Helper Functions ---
def save_query(question, answer):
    df = pd.read_csv(QUERY_FILE)
    new_row = pd.DataFrame([[datetime.now(), question, answer]], columns=["timestamp", "question", "answer"])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(QUERY_FILE, index=False)

def load_queries():
    return pd.read_csv(QUERY_FILE)

def ask_ai(context, question):
    """Query the AI model using OpenRouter (Free Model Only)"""
    try:
        response = client.chat.completions.create(
            model="mistralai/mistral-7b-instruct",  # free model
            messages=[
                {"role": "system", "content": "You are a policy assistant that helps answer questions about company policies."},
                {"role": "user", "content": f"Policy Document:\n{context}\n\nQuestion:\n{question}"}
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

# --- TAB 1: Chat & Upload ---
if page == "💬 Chat & Upload":
    st.title("💬 Policy Chat Assistant")
    st.write("Upload a policy document (PDF or TXT) and ask questions about it.")

    uploaded_file = st.file_uploader("Upload Policy Document", type=["txt", "pdf"])

    if uploaded_file:
        import io
        import PyPDF2

        if uploaded_file.type == "application/pdf":
            reader = PyPDF2.PdfReader(uploaded_file)
            policy_text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
        else:
            policy_text = uploaded_file.read().decode("utf-8")

        st.success("✅ Document uploaded successfully!")

        question = st.text_input("Ask a policy-related question:")
        if st.button("Ask"):
            if question.strip():
                with st.spinner("Thinking..."):
                    answer = ask_ai(policy_text[:4000], question)  # limit context for token safety
                    st.markdown(f"**Answer:** {answer}")
                    save_query(question, answer)
            else:
                st.warning("Please enter a question.")

# --- TAB 2: Analytics ---
elif page == "📊 Analytics":
    st.title("📊 Policy Query Analytics")
    df = load_queries()

    if not df.empty:
        st.write(f"Total Queries: {len(df)}")

        # Most frequent questions
        question_counts = df["question"].value_counts().reset_index()
        question_counts.columns = ["question", "count"]

        # Plot
        fig = px.bar(question_counts.head(10), x="question", y="count", title="🔥 Top 10 Frequently Asked Questions")
        st.plotly_chart(fig, use_container_width=True)

        # Recent questions
        st.subheader("🕓 Recent Questions")
        st.dataframe(df.sort_values("timestamp", ascending=False).head(10))
    else:
        st.info("No queries found yet. Ask something in the Chat tab!")

# --- TAB 3: Contacts ---
elif page == "📞 Contacts":
    st.title("📞 Department Contacts")
    st.write("Reach out to the respective departments for further clarification:")

    contact_data = {
        "Department": ["HR", "Finance", "Legal", "IT Support", "Admin"],
        "Email": [
            "hr@company.in",
            "finance@company.in",
            "legal@company.in",
            "itsupport@company.in",
            "admin@company.in"
        ]
    }
    contact_df = pd.DataFrame(contact_data)
    st.table(contact_df)
    st.success("For urgent queries, please contact HR via email.")