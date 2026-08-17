import openpyxl

wb = openpyxl.load_workbook("PLANTILLA CON INFORME.xlsx", data_only=True)
ws = wb["Resumen"]

for row in range(1, 150):
    for col in range(1, 5):
        val = ws.cell(row=row, column=col).value
        if isinstance(val, str) and val.strip() in [
            "Títulos",
            "Ideas de subtítulos",
            "Keywords",
            "Ejes Estratégicos",
            "Enfoque",
            "Propuesta de artículo + títulos SEO",
            "Propuestas de artículos + títulos SEO",
        ]:
            print(f"Row {row}, Col {col}: {val}")
