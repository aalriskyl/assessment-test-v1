"""Synthetic, labeled source PDFs for local extraction and optional live AI evaluation."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "samples"
OUT.mkdir(parents=True, exist_ok=True)
for slug, supplier, reference, lead, price in [
    ("quotation-fast", "PT Sumber Teknologi", "QUO-FAST-001", 5, 8000000),
    ("quotation-value", "CV Kantor Sejahtera", "QUO-VALUE-001", 14, 7700000),
]:
    pdf = canvas.Canvas(str(OUT / f"{slug}.pdf"))
    pdf.setTitle(f"Synthetic quotation {reference}")
    pdf.setFillColor(HexColor("#21664F"))
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawString(48, 775, "Supplier quotation")
    pdf.setFont("Helvetica", 11)
    pdf.setFillColor(HexColor("#263F32"))
    rows = [f"Supplier: {supplier}", f"Reference: {reference}", f"Lead days: {lead}", "Currency: IDR", "", f"Item: Lounge sofa | 1 | unit | {price}", "", f"Total: IDR {price:,}", "Prices exclude tax and discounts.", "", "Synthetic assessment fixture. No real supplier offer or commitment."]
    for index, row in enumerate(rows):
        pdf.drawString(48, 710-index*27, row)
    pdf.save()
print("Generated two synthetic sample quotation PDFs.")
