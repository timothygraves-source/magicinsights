"""The Magic Insights Machine — Streamlit app for generating CI findings documents."""

import streamlit as st
import tempfile
import os
import json
from transcript_reader import combine_transcripts
from ai_client import call_gateway
from docx_generator import generate_docx

st.set_page_config(
    page_title="The Magic Insights Machine",
    page_icon="✨",
    layout="centered",
)

# Header
st.markdown(
    """
    <h1 style='color:#022D60; font-size:2.2rem; margin-bottom:0;'>The Magic Insights Machine</h1>
    <p style='color:#0C9DDA; font-size:1.1rem; margin-top:4px;'>
        Salesforce Marketing — Customer Insights Team
    </p>
    <hr style='border-color:#0C9DDA; margin-top:8px;'>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    "Upload your interview transcripts, describe what you're trying to learn, and get a "
    "formatted insights document ready to share."
)

# --- Step 1: Upload transcripts ---
st.markdown("### 1. Upload Transcripts")
uploaded_files = st.file_uploader(
    "Upload one or more PDF or Word documents",
    type=["pdf", "docx", "doc"],
    accept_multiple_files=True,
    help="You can upload multiple transcripts — they'll all be analyzed together.",
)

if uploaded_files:
    st.success(f"{len(uploaded_files)} file(s) uploaded: {', '.join(f.name for f in uploaded_files)}")

# --- Step 2: Context ---
st.markdown("### 2. Research Context")

col1, col2 = st.columns(2)
with col1:
    product_name = st.text_input(
        "Product or topic name",
        placeholder="e.g. Agentforce Operations",
        help="This will appear in the document title and throughout the findings.",
    )
with col2:
    event_name = st.text_input(
        "Event or research context",
        placeholder="e.g. World Tour NYC  |  April 2025",
        help="Where and when the interviews were conducted.",
    )

# --- Step 3: Objectives ---
st.markdown("### 3. Research Objectives")
objectives = st.text_area(
    "What are you trying to learn? (one objective per line)",
    placeholder=(
        "Understand which use cases resonate most with customers\n"
        "Assess messaging clarity and differentiation\n"
        "Identify implementation concerns and objections\n"
        "Surface requests for future product development"
    ),
    height=140,
    help="Be specific — the more precise your objectives, the sharper the findings.",
)

# --- Generate button ---
st.markdown("---")

generate_clicked = st.button(
    "✨ Generate Insights",
    type="primary",
    disabled=not (uploaded_files and product_name and event_name and objectives),
    use_container_width=True,
)

if not (uploaded_files and product_name and event_name and objectives):
    st.caption("Fill in all fields above to enable the Generate button.")

# --- Generation flow ---
if generate_clicked:
    gateway_url = st.secrets.get("GATEWAY_URL", "")
    api_key = st.secrets.get("GATEWAY_API_KEY", "")
    model_id = st.secrets.get("MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")

    if not gateway_url or not api_key:
        st.error(
            "Gateway credentials are not configured. "
            "Ask your admin to add GATEWAY_URL and GATEWAY_API_KEY to the app secrets."
        )
        st.stop()

    with st.status("Generating your insights document...", expanded=True) as status:
        try:
            st.write("Reading transcripts...")
            transcripts_text = combine_transcripts(uploaded_files)
            st.write(f"Extracted text from {len(uploaded_files)} file(s).")

            st.write("Analyzing transcripts with Claude...")
            findings = call_gateway(
                transcripts=transcripts_text,
                objectives=objectives,
                event_name=event_name,
                product_name=product_name,
                gateway_url=gateway_url,
                api_key=api_key,
                model_id=model_id,
            )
            st.write("Analysis complete. Building document...")

            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
                output_path = tmp.name

            generate_docx(findings, output_path)

            safe_product = product_name.replace(" ", "_").replace("/", "-")
            safe_event = event_name.split("|")[0].strip().replace(" ", "_")
            filename = f"{safe_product}_CI_Findings_{safe_event}.docx"

            with open(output_path, "rb") as f:
                docx_bytes = f.read()
            os.unlink(output_path)

            status.update(label="Your insights document is ready!", state="complete")

            st.download_button(
                label="Download Insights Document (.docx)",
                data=docx_bytes,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                type="primary",
                use_container_width=True,
            )

        except Exception as e:
            status.update(label="Something went wrong.", state="error")
            st.error(f"Error: {e}")
            st.stop()

# Footer
st.markdown("---")
st.markdown(
    "<p style='font-size:0.8rem; color:#888;'>"
    "This tool was created with the help of generative AI tools and is used by the "
    "Salesforce Marketing Customer Insights team."
    "</p>",
    unsafe_allow_html=True,
)
