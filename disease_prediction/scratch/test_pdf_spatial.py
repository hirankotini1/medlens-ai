import io
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from pypdf import PdfReader, PdfWriter

def create_columnar_pdf():
    # Construct a raw PDF with 4 separate text blocks (one for each column)
    # This simulates how columnar PDFs draw parameter names first, then values, then units, then ref ranges.
    stream_content = """
BT
/F1 10 Tf
50 700 Td
(Hemoglobin) Tj
0 -20 Td
(RBC Count) Tj
0 -20 Td
(WBC Count) Tj
0 -20 Td
(Platelet Count) Tj
0 -20 Td
(Total Bilirubin) Tj
0 -20 Td
(Direct Bilirubin) Tj
0 -20 Td
(ALT) Tj
0 -20 Td
(AST) Tj
0 -20 Td
(ALP) Tj
0 -20 Td
(Total Protein) Tj
0 -20 Td
(Albumin) Tj
0 -20 Td
(Ferritin) Tj
0 -20 Td
(Serum Iron) Tj
0 -20 Td
(Transferrin Saturation) Tj
0 -20 Td
(TIBC) Tj
0 -20 Td
(CRP) Tj
0 -20 Td
(Ceruloplasmin) Tj
0 -20 Td
(Serum Copper) Tj
0 -20 Td
(24-Hour Urinary Copper) Tj
0 -20 Td
(LDH) Tj
0 -20 Td
(Haptoglobin) Tj
0 -20 Td
(Reticulocyte Count) Tj
0 -20 Td
(TSH) Tj
0 -20 Td
(T3) Tj
0 -20 Td
(T4) Tj
0 -20 Td
(T3 Resin Uptake) Tj
ET
BT
/F1 10 Tf
220 700 Td
(14.8) Tj
0 -20 Td
(5.0) Tj
0 -20 Td
(6800) Tj
0 -20 Td
(230000) Tj
0 -20 Td
(1.1) Tj
0 -20 Td
(0.3) Tj
0 -20 Td
(95) Tj
0 -20 Td
(82) Tj
0 -20 Td
(105) Tj
0 -20 Td
(7.3) Tj
0 -20 Td
(4.0) Tj
0 -20 Td
(1250) Tj
0 -20 Td
(220) Tj
0 -20 Td
(78) Tj
0 -20 Td
(280) Tj
0 -20 Td
(2.0) Tj
0 -20 Td
(28) Tj
0 -20 Td
(100) Tj
0 -20 Td
(35) Tj
0 -20 Td
(210) Tj
0 -20 Td
(120) Tj
0 -20 Td
(1.2) Tj
0 -20 Td
(2.0) Tj
0 -20 Td
(1.2) Tj
0 -20 Td
(8.0) Tj
0 -20 Td
(32) Tj
ET
BT
/F1 10 Tf
280 700 Td
(g/dL) Tj
0 -20 Td
(million/uL) Tj
0 -20 Td
(/uL) Tj
0 -20 Td
(/uL) Tj
0 -20 Td
(mg/dL) Tj
0 -20 Td
(mg/dL) Tj
0 -20 Td
(U/L) Tj
0 -20 Td
(U/L) Tj
0 -20 Td
(U/L) Tj
0 -20 Td
(g/dL) Tj
0 -20 Td
(g/dL) Tj
0 -20 Td
(ng/mL) Tj
0 -20 Td
(ug/dL) Tj
0 -20 Td
(%) Tj
0 -20 Td
(ug/dL) Tj
0 -20 Td
(mg/L) Tj
0 -20 Td
(mg/dL) Tj
0 -20 Td
(ug/dL) Tj
0 -20 Td
(ug/24h) Tj
0 -20 Td
(U/L) Tj
0 -20 Td
(mg/dL) Tj
0 -20 Td
(%) Tj
0 -20 Td
(uIU/mL) Tj
0 -20 Td
(ng/mL) Tj
0 -20 Td
(ug/dL) Tj
0 -20 Td
(%) Tj
ET
BT
/F1 10 Tf
360 700 Td
(13.0-17.0) Tj
0 -20 Td
(4.5-5.9) Tj
0 -20 Td
(4000-11000) Tj
0 -20 Td
(150000-450000) Tj
0 -20 Td
(0.2-1.2) Tj
0 -20 Td
(0.0-0.3) Tj
0 -20 Td
(10-40) Tj
0 -20 Td
(10-40) Tj
0 -20 Td
(44-147) Tj
0 -20 Td
(6.0-8.3) Tj
0 -20 Td
(3.5-5.0) Tj
0 -20 Td
(30-400) Tj
0 -20 Td
(60-170) Tj
0 -20 Td
(20-50) Tj
0 -20 Td
(250-450) Tj
0 -20 Td
(0-5) Tj
0 -20 Td
(20-40) Tj
0 -20 Td
(70-140) Tj
0 -20 Td
(10-60) Tj
0 -20 Td
(140-280) Tj
0 -20 Td
(30-200) Tj
0 -20 Td
(0.5-2.5) Tj
0 -20 Td
(0.40-4.20) Tj
0 -20 Td
(0.8-2.0) Tj
0 -20 Td
(4.5-12.0) Tj
0 -20 Td
(24-39) Tj
ET
"""
    stream_bytes = stream_content.encode("latin1")
    pdf_template = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length {len(stream_bytes)} >>
stream
{stream_content}
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000242 00000 n 
0000000{242 + len(stream_bytes) + 40:03d} 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
{242 + len(stream_bytes) + 120}
%%EOF"""
    return pdf_template.encode("latin1")

pdf_bytes = create_columnar_pdf()
reader = PdfReader(io.BytesIO(pdf_bytes))
page = reader.pages[0]

print("=== 1. DEFAULT extract_text() ===")
plain_text = page.extract_text()
print(plain_text[:300], "...\n(Total length:", len(plain_text), ")")

print("\n=== 2. LAYOUT extract_text(extraction_mode='layout') ===")
layout_text = page.extract_text(extraction_mode="layout")
print(layout_text[:400])

from disease_prediction.api.report_extractor import extract_parameters_from_text

print("\n=== Extracted with PLAIN TEXT ===")
res_plain = extract_parameters_from_text(plain_text)
print(f"Count: {len(res_plain)}")
for r in res_plain:
    print(r["parameter"], "=> Val:", r["value"], "Unit:", r["unit"], "Ref:", r["reference_range"])

print("\n=== Extracted with LAYOUT TEXT ===")
res_layout = extract_parameters_from_text(layout_text)
print(f"Count: {len(res_layout)}")
for r in res_layout:
    print(r["parameter"], "=> Val:", r["value"], "Unit:", r["unit"], "Ref:", r["reference_range"])
