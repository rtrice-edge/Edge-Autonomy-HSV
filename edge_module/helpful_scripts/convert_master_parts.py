import openpyxl

def read_excel_file(file_path):
    # Load the workbook
    workbook = openpyxl.load_workbook(file_path)
    
    # Get the active sheet (or you can specify a sheet by name)
    sheet = workbook.active
    
    # Iterate through rows and columns
    for row in sheet.iter_rows(values_only=True):
        # Process each row
        print(row)  # For now, we'll just print each row
        
        # You can access individual cell values like this:
        # for cell in row:
        #     print(cell)
        
        # Add your parsing logic here

# Usage
file_path = "Master Parts.xlsx"
read_excel_file(file_path)
