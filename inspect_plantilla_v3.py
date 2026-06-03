import openpyxl

wb = openpyxl.load_workbook("PLANTILLA CON INFORME.xlsx", data_only=True)
ws = wb["Resumen"]

for row in range(40, 100):
    val = ws.cell(row=row, column=1).value
    if val is not None and str(val).strip() != "":
        print(f"Row {row}: {val}")
