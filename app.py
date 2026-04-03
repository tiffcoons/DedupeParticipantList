import streamlit as st
import pandas as pd
import json

from bq_query import run_participant_query

st.set_page_config(page_title="Dedupe Participant List", layout="wide")
st.title("Dedupe Participant List")

# ─────────────────────────────────────────────
# Step 1: Load Participant List
# ─────────────────────────────────────────────
st.header("Step 1: Load Participant List")

source = st.radio(
    "Select data source:",
    ["Upload CSV", "Connect to BigQuery"],
    horizontal=True,
)

# Clear stored data when the user switches source
if st.session_state.get("last_source") != source:
    st.session_state.pop("participant_df", None)
    st.session_state["last_source"] = source

# ── CSV path ──────────────────────────────────
if source == "Upload CSV":
    uploaded = st.file_uploader("Upload participant list CSV", type=["csv"])
    if uploaded is not None:
        df = pd.read_csv(uploaded)
        st.session_state["participant_df"] = df
        st.success(f"Loaded {len(df):,} rows from CSV.")

# ── BigQuery path ─────────────────────────────
else:
    st.subheader("BigQuery Query Parameters")

    col1, col2, col3 = st.columns(3)
    with col1:
        sign_up_solution_id = st.number_input(
            "Sign Up Solution ID",
            min_value=0,
            step=1,
            value=None,
            placeholder="e.g. 123456",
            format="%d",
        )
    with col2:
        program_solution_id = st.number_input(
            "Program Solution ID",
            min_value=0,
            step=1,
            value=None,
            placeholder="e.g. 789012",
            format="%d",
        )
    with col3:
        feedback_limit = st.number_input(
            "Feedback Limit",
            min_value=1,
            step=1,
            value=None,
            placeholder="e.g. 100",
            format="%d",
        )

    with st.expander("Affiliation Business Keys (optional)"):
        col4, col5, col6 = st.columns(3)
        with col4:
            affil_1 = st.text_input("Affiliation 1 Business Key", placeholder="e.g. affiliation")
        with col5:
            affil_2 = st.text_input("Affiliation 2 Business Key", placeholder="e.g. affil_secondary")
        with col6:
            affil_3 = st.text_input("Affiliation 3 Business Key", placeholder="e.g. affil_tertiary")

    with st.expander("BigQuery Credentials"):
        auth_method = st.radio(
            "Authentication:",
            ["Application Default Credentials (ADC)", "Upload Service Account JSON"],
            horizontal=True,
        )
        credentials = None
        if auth_method == "Upload Service Account JSON":
            key_file = st.file_uploader("Service account JSON key", type=["json"])
            if key_file:
                from google.oauth2 import service_account
                creds_data = json.load(key_file)
                credentials = service_account.Credentials.from_service_account_info(
                    creds_data,
                    scopes=["https://www.googleapis.com/auth/bigquery"],
                )
                st.success("Service account loaded.")

    required_filled = (
        sign_up_solution_id is not None
        and program_solution_id is not None
        and feedback_limit is not None
    )

    if not required_filled:
        st.info("Fill in Sign Up Solution ID, Program Solution ID, and Feedback Limit to enable the query.")

    if st.button("Run Query", type="primary", disabled=not required_filled):
        with st.spinner("Running BigQuery query…"):
            try:
                df = run_participant_query(
                    sign_up_solution_id=int(sign_up_solution_id),
                    program_solution_id=int(program_solution_id),
                    feedback_limit=int(feedback_limit),
                    affil_1=affil_1 or "",
                    affil_2=affil_2 or "",
                    affil_3=affil_3 or "",
                    credentials=credentials,
                )
                st.session_state["participant_df"] = df
                st.success(f"Query returned {len(df):,} rows.")
            except Exception as e:
                st.error(f"Query failed: {e}")

# ─────────────────────────────────────────────
# Downstream processing (same for both sources)
# ─────────────────────────────────────────────
df = st.session_state.get("participant_df")

if df is not None:
    st.divider()
    st.subheader(f"Participant List — {len(df):,} rows")
    st.dataframe(df, use_container_width=True)

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download as CSV",
        data=csv_bytes,
        file_name="participant_list.csv",
        mime="text/csv",
    )
