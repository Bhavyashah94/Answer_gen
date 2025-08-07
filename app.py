import os
import streamlit as st
import google.generativeai as genai
import tempfile
import subprocess
import shutil
import markdown2
import time
from collections import deque

MAX_REQUESTS_PER_MIN = 15
RATE_LIMIT_WINDOW = 60  # seconds
BUFFER_SECONDS = 5

request_timestamps = deque()

def rate_limit():
    current_time = time.time()

    # Remove old timestamps outside the 60-sec window
    while request_timestamps and current_time - request_timestamps[0] > RATE_LIMIT_WINDOW:
        request_timestamps.popleft()

    if len(request_timestamps) >= MAX_REQUESTS_PER_MIN:
        wait_time = RATE_LIMIT_WINDOW - (current_time - request_timestamps[0]) + BUFFER_SECONDS
        placeholder = st.empty()
        for remaining in range(int(wait_time), 0, -1):
            placeholder.warning(f"⏳ Rate limit reached. Waiting {remaining} seconds...")
            time.sleep(1)
        placeholder.empty()
        rate_limit()

    request_timestamps.append(time.time())


# === CONFIG ===
st.set_page_config(page_title="Gemini QA to PDF", layout="centered")

# === Gemini Setup ===

# Try from secrets first
if "GEMINI_API_KEY" in st.secrets:
    st.session_state.api_key = st.secrets["GEMINI_API_KEY"]

# Input field if not already in session
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

if not st.session_state.api_key:
    st.session_state.api_key = st.text_input("🔐 Enter your Gemini API Key", type="password")

if st.session_state.api_key:
    try:
        os.environ["GOOGLE_API_KEY"] = st.session_state.api_key
        genai.configure(api_key=st.session_state.api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        st.success("✅ API Key accepted.")
    except Exception as e:
        st.error(f"❌ Failed to configure Gemini: {e}")

    if st.button("🔓 Clear API Key"):
        del st.session_state.api_key
        st.rerun()

# === Functions ===
def get_questions_from_txt(uploaded_file):
    content = uploaded_file.read().decode("utf-8")
    return [line.strip() for line in content.splitlines() if line.strip()]

def get_gemini_answer(question):
    response = model.generate_content(question)
    return response.text.strip()

def generate_markdown_from_qa(qa_pairs):
    style = (
        "<style>\n"
        "table { width: 100%; border-collapse: collapse; }\n"
        "th, td { padding: 8px 12px; border: 1px solid #ccc; }\n"
        "</style>\n\n"
    )
    md = style
    for idx, (q, a_md) in enumerate(qa_pairs, 1):
        md += f"## Q{idx}: {q}\n\n{a_md.strip()}\n\n---\n\n"
    return md

def convert_md_to_pdf(md_content):
    if not shutil.which("pandoc"):
        raise RuntimeError("Pandoc is not installed or not in PATH. Please install it from https://pandoc.org/installing.html")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".md", mode="w", encoding="utf-8") as tmp_md:
        tmp_md.write(md_content)
        tmp_md_path = tmp_md.name

    docx_path = tmp_md_path.replace(".md", ".docx")
    pdf_path = tmp_md_path.replace(".md", ".pdf")

    # Step 1: Convert MD to DOCX
    docx_cmd = ["pandoc", tmp_md_path, "-o", docx_path]
    subprocess.run(docx_cmd, check=True)

    # Step 2: Convert DOCX to PDF (this uses Word on Windows or LibreOffice if installed)
    # Try using LibreOffice for cross-platform conversion
    libreoffice_cmd = ["libreoffice", "--headless", "--convert-to", "pdf", docx_path, "--outdir", os.path.dirname(pdf_path)]
    subprocess.run(libreoffice_cmd, check=True)

    with open(pdf_path, "rb") as pdf_file:
        return pdf_file.read()

# === Streamlit App ===
st.title("📄 Gemini QA to PDF Generator")
st.markdown("Upload a `.txt` file with your questions, and get AI-generated answers exported as a styled PDF.")

footer = """
<style>
.footer {
    margin-top: 3rem;
    text-align: center;
    padding: 1rem 0;
    font-size: 14px;
    color: #aaa;
    border-top: 1px solid #444;
}
</style>
<div class="footer">
  <div style="max-width: 800px; margin: auto;">
    Made with ❤️ by Bhavya Shah | Answer_Gen Project
  </div>
</div>
"""



uploaded_file = st.file_uploader("Upload Questions File (.txt)", type=["txt"])

if uploaded_file and st.session_state.api_key:
    questions = get_questions_from_txt(uploaded_file)
    qa_pairs = []

    with st.spinner("Generating answers..."):
        for idx, question in enumerate(questions, 1):
            st.markdown(f"**Q{idx}:** {question}")
            try:
                rate_limit()
                answer = get_gemini_answer(question)
                qa_pairs.append((question, answer))
                st.markdown(markdown2.markdown(answer))
                st.divider()
            except Exception as e:
                st.error(f"Failed to get answer for Q{idx}: {e}")
                qa_pairs.append((question, "*Error fetching answer.*"))

    if qa_pairs:
        st.success("✅ All questions answered. Generating PDF...")
        try:
            md = generate_markdown_from_qa(qa_pairs)
            pdf_bytes = convert_md_to_pdf(md)

            st.download_button(
                label="📥 Download Answers PDF",
                data=pdf_bytes,
                file_name="Gemini_Answers.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"❌ Failed to generate PDF: {e}")
            
st.markdown(footer, unsafe_allow_html=True)