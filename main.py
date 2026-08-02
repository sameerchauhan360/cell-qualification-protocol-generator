import os
import tempfile

import streamlit as st

from app.graph import compiled_graph

st.set_page_config(
    page_title="Cell Qualification Protocol Generator",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🔋 Cell Qualification Protocol (CQP) Generator")
st.markdown(
    "**Automated ingestion and generation under regulatory framework IESF-4400**"
)

with st.sidebar:
    st.markdown("### About the System")
    st.write(
        "This tool automates the assembly of a formal Cell Qualification Protocol (CQP) `.docx` document. "
        "It ingests battery cell documents, runs a parallel extraction graph (using LangGraph), parses tables, "
        "queries stepfun-ai/step-3.7-flash (via NVIDIA API) for datasheet tables inside images, "
        "and injects the dynamic rows/sections while maintaining layout styles and editing locks."
    )
    st.divider()
    st.info(
        "Ensure your `.env` contains a valid `NVIDIA_API_KEY` for the NVIDIA proxy."
    )

col_inputs, col_results = st.columns([1, 1], gap="large")

with col_inputs:
    st.markdown("### 📥 Upload Ingestion Files")
    st.write(
        "Upload the three cell specification source files to execute the generator graph:"
    )

    tmp_file = st.file_uploader(
        "1. Test Method Procedure (TMP) — docx format",
        type=["docx"],
        help="Prose containing equipment and sample preparation procedures",
    )

    acl_file = st.file_uploader(
        "2. Acceptance Criteria & Limits (ACL) — docx format",
        type=["docx"],
        help="Tables organizing tests and limit specifications per duty profile",
    )

    pdf_file = st.file_uploader(
        "3. Vendor Product Datasheet — pdf format",
        type=["pdf"],
        help="Product datasheet containing electrical ratings, production grading tables, and packaging info",
    )

    st.divider()
    st.markdown("### 🔧 Operator Inputs")
    market_input = st.text_input(
        "Target Market (optional)",
        placeholder="Defaults based on cell model (e.g., EU / UN-38.3, US / DOT)",
        help="Sets the target market framework token in the CQP report",
    )

    generate_btn = st.button("🚀 Generate Protocol", use_container_width=True)


def save_uploaded_to_temp(uploaded_file, suffix):
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as tmp:
        tmp.write(uploaded_file.getvalue())
    return path


with col_results:
    st.markdown("### 📄 Generation Results")

    if generate_btn:
        if not tmp_file or not acl_file or not pdf_file:
            st.error(
                "❌ Please upload all three required source files before generating."
            )
        else:
            tmp_temp = save_uploaded_to_temp(tmp_file, ".docx")
            acl_temp = save_uploaded_to_temp(acl_file, ".docx")
            pdf_temp = save_uploaded_to_temp(pdf_file, ".pdf")
            out_temp = tempfile.mktemp(suffix=".docx")

            market_val = market_input.strip()
            if not market_val:
                name_upper = pdf_file.name.upper()
                if "CYG" in name_upper:
                    market_val = "EU / UN-38.3"
                elif "AUR" in name_upper:
                    market_val = "US / DOT"
                else:
                    market_val = "Global"

            initial_state = {
                "tmp_path": tmp_temp,
                "acl_path": acl_temp,
                "pdf_path": pdf_temp,
                "market": market_val,
                "output_path": out_temp,
                "pdf_data": {},
                "tmp_data": {},
                "acl_data": {},
                "extracted_data": {},
                "error": "",
            }

            status_container = st.empty()
            try:
                with status_container.container():
                    st.info("⏳ Processing ingestion files...")

                with st.spinner("Executing extraction graph & building document..."):
                    final_state = compiled_graph.invoke(initial_state)

                if final_state.get("error"):
                    status_container.error(
                        f"❌ Generation Failed: {final_state['error']}"
                    )
                else:
                    status_container.success("🎉 Protocol Generated Successfully!")
                    data = final_state["extracted_data"]

                    st.markdown("#### 🔍 Extracted Specifications Preview")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Cell Model:** `{data['cell_model']}`")
                        st.markdown(
                            f"**Manufacturer:** `{data['manufacturer_from_datasheet']}`"
                        )
                        st.markdown(f"**Format:** `{data['format_from_datasheet']}`")
                        st.markdown(f"**Chemistry:** `{data['chemistry']}`")
                        st.markdown(f"**Rated Capacity:** `{data['rated_capacity']}`")
                        st.markdown(f"**Document No:** `{data['doc_number']}`")
                    with col2:
                        st.markdown(f"**Nominal Voltage:** `{data['nominal_voltage']}`")
                        st.markdown(f"**Max Charge Voltage:** `{data['v_max']}`")
                        st.markdown(f"**Min Discharge Voltage:** `{data['v_min']}`")
                        st.markdown(
                            f"**Grading Band:** `{data['grading_low']} to {data['grading_high']}`"
                        )
                        st.markdown(f"**Market:** `{data['market']}`")
                        st.markdown(
                            f"**Duty Profiles:** `{data['duty_profiles_joined']}`"
                        )

                    st.text_area(
                        "Storage Condition (Extracted)",
                        value=data["storage_from_datasheet"],
                        disabled=True,
                        height=65,
                    )
                    st.text_area(
                        "Supplied As (Extracted)",
                        value=data["supplied_as_from_datasheet"],
                        disabled=True,
                        height=65,
                    )

                    st.divider()

                    with open(out_temp, "rb") as f:
                        generated_bytes = f.read()

                    st.download_button(
                        label="💾 Download Generated Protocol (.docx)",
                        data=generated_bytes,
                        file_name=f"CQP_{data['cell_model']}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                    )
            except Exception as e:
                status_container.error(f"❌ An unexpected error occurred: {e}")
            finally:
                for path in [tmp_temp, acl_temp, pdf_temp]:
                    if os.path.exists(path):
                        try:
                            os.remove(path)
                        except Exception:
                            pass
    else:
        st.write(
            "Ready to ingest files. Upload source files on the left and click **Generate Protocol** to begin."
        )
