# Cell Qualification Protocol (CQP) Generator

An automated tool built with **LangGraph** and **Streamlit** to ingest battery cell specifications and dynamically generate formal, protected CQP Word documents under the **IESF-4400** regulatory framework.

---

## Deliverables Summary

This repository includes all required deliverables for the NCQL assignment:
* **The Ingestion & Generation Engine:** A parallel-node state graph for concurrent document extraction.
* **The Web Frontend:** A clean, native Streamlit interface to run the generator on `localhost` (with file uploaders and preview card features).
* **Generated Protocols:** Pre-generated dynamic `.docx` protocols for **Set A, Set B, and Set C** located in the `output/` directory.
* **`SOLUTION.md`:** Writeup detailing the system architecture, OpenXML manipulation methods, assumptions, and constraints.

---

## Repository Structure

```
.
├── app/
│   ├── doc_parsers.py    # Custom docx parser (TMP and ACL)
│   ├── docx_editor.py    # OpenXML template customize (merges, cloning, protection)
│   ├── graph.py          # Parallel ingestion LangGraph flow definition
│   └── pdf_parser.py     # pdfplumber text parsing & ChatNVIDIA vision LLM query
├── output/
│   ├── CQP_CYG-21700-50G.docx  # Generated output for Set A (matches GOLD 100%)
│   ├── CQP_AUR-PR-340.docx     # Generated output for Set B (dynamic 1-profile)
│   └── CQP_PLX-PCH-088.docx    # Generated output for Set C (dynamic 3-profile)
├── main.py               # Streamlit web UI entrypoint
├── requirements.txt      # Python dependencies list
├── SOLUTION.md           # System design & architecture write-up
└── README.md             # This setup file
```

---

## System Ingestion Workflow

Below is the dynamic extraction graph diagram showing how the data from the source files is parsed in parallel and compiled into the final CQP document:

![System Ingestion Workflow](workflow.png)

---

## How to Setup & Run

### 1. Set Up Python Environment
Ensure you have Python 3.12+ installed. Create and activate a virtual environment, then install requirements:

```powershell
# Setup venv
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Your NVIDIA API Key
Create a `.env` file in the root directory and add your NVIDIA Integration Proxy API Key:
```env
NVIDIA_API_KEY="your-nvapi-key-here"
```
*(Ensure the key starts with `nvapi-` if using the NVIDIA endpoints).*

### 3. Run the Web Interface
Start the Streamlit server on your local machine:
```powershell
.venv\Scripts\python.exe -m streamlit run main.py
```
This will automatically launch your browser and open the UI at `http://localhost:8501`.

### 4. Run the CLI Test Harness (Optional)
To execute the generation pipeline for all three sets directly from the command line:
```powershell
.venv\Scripts\python.exe -m app.graph
```
Generated documents will be written/updated in the `output/` directory.

---

For technical details, low-level XML merging logic, and engineering assumptions, please refer to [SOLUTION.md](file:///d:/Agentic%20Ai/Assignment/AIMl%20Engineer-Webosphere/SOLUTION.md).
