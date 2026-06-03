import os
from markdown_pdf import MarkdownPdf, Section

md_path = r"C:\Users\photo\.gemini\antigravity\brain\ebac7c2d-e1f3-4dc8-a846-0a0814803d04\KeySearch_V6_Architecture_Report.md"
pdf_path = r"C:\Users\photo\.gemini\antigravity\brain\ebac7c2d-e1f3-4dc8-a846-0a0814803d04\KeySearch_V6_Architecture_Report.pdf"

print("Leyendo markdown...")
with open(md_path, "r", encoding="utf-8") as f:
    text = f.read()

print("Generando PDF...")
pdf = MarkdownPdf(toc_level=2)
pdf.add_section(Section(text))
pdf.save(pdf_path)
print("¡PDF generado exitosamente!")
