import os
from typing import Any, Dict, TypedDict

from langgraph.graph import END, START, StateGraph

from app.doc_parsers import parse_acl_document, parse_tmp_document
from app.docx_editor import render_protocol_docx
from app.pdf_parser import extract_pdf_data


class GenerationState(TypedDict):
    """LangGraph state schema for holding parsing results and parameters."""

    tmp_path: str
    acl_path: str
    pdf_path: str
    market: str
    output_path: str
    pdf_data: Dict[str, Any]
    tmp_data: Dict[str, Any]
    acl_data: Dict[str, Any]
    extracted_data: Dict[str, Any]
    error: str


def parse_pdf_node(state: GenerationState) -> Dict[str, Any]:
    """State node to extract specs and grading lot limits from the vendor datasheet."""
    pdf_path = state.get("pdf_path")
    print("--- Node: parse_pdf ---")
    print(f"Parsing PDF: {os.path.basename(pdf_path)}")
    try:
        data = extract_pdf_data(pdf_path)
        return {"pdf_data": data}
    except Exception as e:
        print(f"Error in parse_pdf_node: {e}")
        return {"error": f"PDF extraction failed: {str(e)}"}


def parse_tmp_node(state: GenerationState) -> Dict[str, Any]:
    """State node to extract title and chemistry from the TMP document."""
    tmp_path = state.get("tmp_path")
    print("--- Node: parse_tmp ---")
    print(f"Parsing TMP: {os.path.basename(tmp_path)}")
    try:
        data = parse_tmp_document(tmp_path)
        return {"tmp_data": data}
    except Exception as e:
        print(f"Error in parse_tmp_node: {e}")
        return {"error": f"TMP extraction failed: {str(e)}"}


def parse_acl_node(state: GenerationState) -> Dict[str, Any]:
    """State node to extract profiles, notes, and limits from the ACL document."""
    acl_path = state.get("acl_path")
    print("--- Node: parse_acl ---")
    print(f"Parsing ACL: {os.path.basename(acl_path)}")
    try:
        data = parse_acl_document(acl_path)
        return {"acl_data": data}
    except Exception as e:
        print(f"Error in parse_acl_node: {e}")
        return {"error": f"ACL extraction failed: {str(e)}"}


def merge_extractions_node(state: GenerationState) -> Dict[str, Any]:
    """State node to join parallel ingestion streams and format tokens."""
    print("--- Node: merge_extractions ---")
    if state.get("error"):
        return {}

    pdf_data = state.get("pdf_data") or {}
    tmp_data = state.get("tmp_data") or {}
    acl_data = state.get("acl_data") or {}
    market = state.get("market") or ""

    try:
        extracted_data = {
            "cell_model": pdf_data.get("cell_model")
            or tmp_data.get("cell_model")
            or "",
            "manufacturer_from_datasheet": pdf_data.get("manufacturer") or "",
            "format_from_datasheet": pdf_data.get("cell_format") or "",
            "chemistry": tmp_data.get("chemistry") or "",
            "market": market,
            "framework": "IESF-4400",
            "lab": "Northgate Cell Qualification Laboratory (NCQL)",
            "tmp_doc_title": tmp_data.get("tmp_doc_title") or "",
            "acl_doc_title": acl_data.get("acl_doc_title") or "",
            "datasheet_title": f"{pdf_data.get('manufacturer')} datasheet — {pdf_data.get('cell_model')}",
            "doc_number": acl_data.get("doc_number") or "",
            "nominal_voltage": pdf_data.get("nominal_voltage") or "",
            "v_max": pdf_data.get("v_max") or "",
            "v_min": pdf_data.get("v_min") or "",
            "rated_capacity": pdf_data.get("rated_capacity") or "",
            "grading_low": pdf_data.get("grading_low") or "",
            "grading_high": pdf_data.get("grading_high") or "",
            "storage_from_datasheet": pdf_data.get("storage_condition") or "",
            "supplied_as_from_datasheet": pdf_data.get("supplied_as") or "",
            "duty_profiles": acl_data.get("duty_profiles") or [],
            "footnotes": acl_data.get("footnotes") or [],
        }

        profile_names = [dp["name"] for dp in extracted_data["duty_profiles"]]
        extracted_data["duty_profiles_joined"] = " & ".join(profile_names)

        return {"extracted_data": extracted_data}
    except Exception as e:
        print(f"Error in merge_extractions_node: {e}")
        return {"error": f"Merge node failed: {str(e)}"}


def render_protocol_node(state: GenerationState) -> Dict[str, Any]:
    """State node to generate and save the dynamic CQP word document."""
    print("--- Node: render_protocol ---")
    if state.get("error"):
        return {}

    extracted_data = state.get("extracted_data")
    output_path = state.get("output_path")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(
        os.path.dirname(current_dir),
        "candidate_pack",
        "candidate_pack",
        "template",
        "CQP_Template.docx",
    )

    print(f"Rendering template: {os.path.basename(template_path)}")
    print(f"Target output: {output_path}")

    try:
        render_protocol_docx(template_path, extracted_data, output_path)
        return {"error": ""}
    except Exception as e:
        print(f"Error in render_protocol_node: {e}")
        return {"error": f"DOCX generation failed: {str(e)}"}


# Build parallel-execution state graph workflow
workflow = StateGraph(GenerationState)

workflow.add_node("parse_pdf", parse_pdf_node)
workflow.add_node("parse_tmp", parse_tmp_node)
workflow.add_node("parse_acl", parse_acl_node)
workflow.add_node("merge_extractions", merge_extractions_node)
workflow.add_node("render_protocol", render_protocol_node)

workflow.add_edge(START, "parse_pdf")
workflow.add_edge(START, "parse_tmp")
workflow.add_edge(START, "parse_acl")

workflow.add_edge("parse_pdf", "merge_extractions")
workflow.add_edge("parse_tmp", "merge_extractions")
workflow.add_edge("parse_acl", "merge_extractions")

workflow.add_edge("merge_extractions", "render_protocol")
workflow.add_edge("render_protocol", END)

compiled_graph = workflow.compile()

if __name__ == "__main__":
    base_input_dir = r"d:\Agentic Ai\Assignment\AIMl Engineer-Webosphere\candidate_pack\candidate_pack\inputs"
    base_output_dir = r"d:\Agentic Ai\Assignment\AIMl Engineer-Webosphere\output"

    sets = {
        "Set A": {
            "tmp": "setA/TMP_CYG-21700-50G.docx",
            "acl": "setA/ACL_CYG-21700-50G.docx",
            "pdf": "setA/DATASHEET_CYG-21700-50G.pdf",
            "market": "EU / UN-38.3",
            "output_name": "CQP_CYG-21700-50G.docx",
        },
        "Set B": {
            "tmp": "setB/TMP_AUR-PR-340.docx",
            "acl": "setB/ACL_AUR-PR-340.docx",
            "pdf": "setB/DATASHEET_AUR-PR-340.pdf",
            "market": "US / DOT",
            "output_name": "CQP_AUR-PR-340.docx",
        },
        "Set C": {
            "tmp": "setC/TMP_PLX-PCH-088.docx",
            "acl": "setC/ACL_PLX-PCH-088.docx",
            "pdf": "setC/DATASHEET_PLX-PCH-088.pdf",
            "market": "Global",
            "output_name": "CQP_PLX-PCH-088.docx",
        },
    }

    for set_name, files in sets.items():
        print("\n==========================================")
        print(f"Running full graph generation for {set_name}")
        print("==========================================")
        initial_state = {
            "tmp_path": os.path.join(base_input_dir, files["tmp"]),
            "acl_path": os.path.join(base_input_dir, files["acl"]),
            "pdf_path": os.path.join(base_input_dir, files["pdf"]),
            "market": files["market"],
            "output_path": os.path.join(base_output_dir, files["output_name"]),
            "pdf_data": {},
            "tmp_data": {},
            "acl_data": {},
            "extracted_data": {},
            "error": "",
        }

        final_state = compiled_graph.invoke(initial_state)
        if final_state.get("error"):
            print(f"Generation FAILED for {set_name}: {final_state['error']}")
        else:
            print(f"Generation SUCCESSFUL for {set_name}!")
            print(f"Output saved to: {final_state['output_path']}")
