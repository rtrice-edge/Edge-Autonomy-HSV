from odoo import models

class CycleCountXlsxReport(models.AbstractModel):
    _name = 'report.cycle_count_xlsx_report'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Cycle Count XLSX Report'

    def generate_xlsx_report(self, workbook, data, cycle_count):
        """
        Generates an Excel report with one sheet that lists all the cycle count log lines
        with a header row and includes Lot/Serial Number, Planned Count Date, Verified By,
        Actual Count Date, and Counted By.
        """
        sheet = workbook.add_worksheet("CycleCount")
        row = 0
        col = 0

        # **Write Header Row (including Actual Count Date and Counted By)**
        headers = ['Part Number', 'Location', 'Lot/Serial Number', 'Planned Count Date', 'Verified By', 'Actual Count Date', 'Counted By', 'Expected Quantity', 'Actual Quantity', 'Difference']
        for header in headers:
            sheet.write(row, col, header)
            col += 1
        row += 1 # Move to the next row for data

        # Iterate over all log lines in the cycle count record
        for log in cycle_count.log_ids:
            col = 0
            # Write each field to a cell (adjust the order as needed)
            sheet.write(row, col, log.product_id.default_code or log.product_id.name)
            col += 1
            sheet.write(row, col, log.location_id.complete_name)
            col += 1
            # **Write Lot/Serial Number**
            sheet.write(row, col, log.lot_id.name if log.lot_id else '')
            col += 1
            # **Write Planned Count Date**
            sheet.write(row, col, log.planned_count_date.strftime('%Y-%m-%d') if log.planned_count_date else '')
            col += 1
            # **Write Verified By (User)**
            sheet.write(row, col, log.user_id.name if log.user_id else '')
            col += 1
            # **Write Actual Count Date**
            sheet.write(row, col, log.actual_count_date.strftime('%Y-%m-%d %H:%M:%S') if log.actual_count_date else '') # Format datetime
            col += 1
            # **Write Counted By (User)**
            sheet.write(row, col, log.user_id.name if log.user_id else '') # Re-using Verified By - clarify if different
            col += 1
            sheet.write(row, col, log.expected_quantity)
            col += 1
            sheet.write(row, col, log.actual_quantity)
            col += 1
            sheet.write(row, col, log.difference)
            row += 1