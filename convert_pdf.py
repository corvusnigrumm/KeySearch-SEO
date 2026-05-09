import os
from markdown_pdf import MarkdownPdf, Section

def convert_md_to_pdf(md_file, pdf_file):
    pdf = MarkdownPdf()
    
    with open(md_file, 'r', encoding='utf-8') as f:
        text = f.read()
        
    pdf.add_section(Section(text))
    pdf.save(pdf_file)
    print(f"Generado exitosamente: {pdf_file}")

if __name__ == "__main__":
    convert_md_to_pdf("Documentacion_Detallada_KeySearch.md", "Documentacion_Detallada_KeySearch.pdf")
