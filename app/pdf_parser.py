import base64
import json
import os

from dotenv import load_dotenv
import pdfplumber
import pypdf
from langchain_core.messages import HumanMessage
from langchain_nvidia_ai_endpoints import ChatNVIDIA

load_dotenv()

api_key = os.environ.get("NVIDIA_API_KEY") or os.environ.get("OPENAI_API_KEY")
if not api_key:
    raise Exception("API KEY not found")

client = ChatNVIDIA(
    model="stepfun-ai/step-3.7-flash",
    nvidia_api_key=api_key,
    temperature=0.1,
    max_completion_tokens=4000,
    timeout=120,
)


def extract_pdf_data(pdf_path):
    extracted_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            extracted_text += f"--- Page {i+1} Text ---\n"
            page_text = page.extract_text()
            if page_text:
                extracted_text += page_text
            extracted_text += "\n"

    reader = pypdf.PdfReader(pdf_path)
    b64_images = []
    for i, page in enumerate(reader.pages):
        for j, image_file in enumerate(page.images):
            img_b64 = base64.b64encode(image_file.data).decode("utf-8")
            b64_images.append(img_b64)

    prompt_text = (
        "You are a precise data extraction assistant. Analyze the following native text extracted from a battery cell datasheet, "
        "along with the attached images of tables and curves from that same datasheet. "
        "Your task is to extract the following 11 values exactly as they appear in the text or images. Include units (V, Ah, °C, etc.) where appropriate:\n\n"
        "1. manufacturer: The name of the manufacturer/vendor (e.g. 'Cygnus Cell Technologies').\n"
        "2. cell_model: The model code/name (e.g. 'CYG-21700-50G').\n"
        "3. cell_format: The mechanical format (e.g. '21700 cylindrical', 'prismatic (hard-case)', 'pouch'). Include size if specified.\n"
        "4. nominal_voltage: The nominal voltage rating (e.g. '3.63 V').\n"
        "5. v_max: The maximum charge voltage limit (e.g. '4.20 V').\n"
        "6. v_min: The minimum discharge cut-off voltage limit (e.g. '2.50 V').\n"
        "7. rated_capacity: The rated/nominal electrical capacity (e.g. '5.00 Ah').\n"
        "8. grading_low: The lowest graded capacity value for production lot selection (with unit, e.g. '4.85 Ah' or '4.85 V' depending on the table. Make sure to look at the 'Lowest graded capacity' or 'Grade C' low limit in the Production Capacity Grading table).\n"
        "9. grading_high: The highest graded capacity value for production lot selection (with unit, e.g. '5.05 Ah' or similar).\n"
        "10. storage_condition: The verbatim sentence explaining the storage temperature, humidity, and/or state-of-charge requirements (e.g. 'Store at 20 ± 5 °C and ...'). Do not abbreviate or change words.\n"
        "11. supplied_as: The verbatim sentence explaining how the cells are packaged or delivered (e.g. 'Supplied as 21700 cylindrical cells, 50 cells per transport tray.').\n\n"
        f"--- EXTRACTED NATIVE TEXT ---\n{extracted_text}\n\n"
        "Output the result ONLY as a valid JSON object. Do not wrap it in markdown code blocks or add any comments or extra text. "
        "Strictly return the JSON with these exact keys:\n"
        "{\n"
        '  "manufacturer": "...",\n'
        '  "cell_model": "...",\n'
        '  "cell_format": "...",\n'
        '  "nominal_voltage": "...",\n'
        '  "v_max": "...",\n'
        '  "v_min": "...",\n'
        '  "rated_capacity": "...",\n'
        '  "grading_low": "...",\n'
        '  "grading_high": "...",\n'
        '  "storage_condition": "...",\n'
        '  "supplied_as": "..."\n'
        "}"
    )

    message_content = [{"type": "text", "text": prompt_text}]
    for img_b64 in b64_images:
        message_content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_b64}"},
            }
        )

    messages = [HumanMessage(content=message_content)]

    response = client.invoke(messages)
    content = response.content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    try:
        data = json.loads(content)
        return data
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON response: {content}")
        raise e


if __name__ == "__main__":
    test_pdf = r"d:\Agentic Ai\Assignment\AIMl Engineer-Webosphere\candidate_pack\candidate_pack\inputs\setA\DATASHEET_CYG-21700-50G.pdf"
    print("Extracting data from test PDF...")
    try:
        extracted = extract_pdf_data(test_pdf)
        print(json.dumps(extracted, indent=2))
    except Exception as e:
        print("Error during test run:", e)
