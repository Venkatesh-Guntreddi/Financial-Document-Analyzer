from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import datetime
import re

def generate_pdf(summary, kpis, ratios, output_path="financial_report.pdf"):
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter
    margin = 40

    # --- Title (Centered) ---
    title = "Smart Financial Summary Agent"
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 50, title)

    # --- Timestamp (Top-left) ---
    c.setFont("Helvetica", 10)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    c.drawString(margin, height - 70, f"Generated on: {now}")

    # --- Begin Body ---
    text = c.beginText(margin, height - 100)
    text.setFont("Helvetica-Bold", 12)
    text.textLine("Executive Summary")
    text.setFont("Helvetica", 11)

    # Clean Markdown (**text**) formatting
    cleaned_summary = re.sub(r"\*\*(.*?)\*\*", r"\1", summary)
    for line in cleaned_summary.strip().split('\n'):
        text.textLine(line)

    # --- KPIs ---
    text.textLine("")
    text.setFont("Helvetica-Bold", 12)
    text.textLine("Key Financial KPIs")
    text.setFont("Helvetica", 11)
    for key, value in kpis.items():
        text.textLine(f"- {key}: {value:,.2f}")

    # --- Ratios ---
    if ratios:
        text.textLine("")
        text.setFont("Helvetica-Bold", 12)
        text.textLine("Financial Ratios")
        text.setFont("Helvetica", 11)
        for key, value in ratios.items():
            text.textLine(f"- {key}: {value}")
    else:
        text.textLine("")
        text.setFont("Helvetica", 11)
        text.textLine("⚠ No financial ratios found.")

    # Finish
    c.drawText(text)
    c.showPage()
    c.save()

    return output_path