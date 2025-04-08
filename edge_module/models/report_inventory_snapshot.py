# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import datetime
import pytz
import logging

_logger = logging.getLogger(__name__)

class ReportInventorySnapshotXlsx(models.AbstractModel):
    _name = 'report.edge_module.report_inventory_snapshot_xlsx' # Replace edge_module
    _description = 'Inventory Snapshot XLSX Report Generator'
    _inherit = 'report.report_xlsx.abstract'

    def _get_snapshot_data_for_report(self, report_wizard):
        # ... (your existing _get_snapshot_data_for_report method remains unchanged) ...
        """
        Helper method to run the query based on the wizard's state.
        Essentially duplicates the logic from _get_inventory_snapshot_lines
        but fetches more data needed for report display names.
        """
        snapshot_date = report_wizard.date_snapshot

        # --- Timezone Handling ---
        user_tz = self.env.user.tz or 'UTC'
        local_tz = pytz.timezone(user_tz)
        naive_end_of_day = datetime.datetime.combine(snapshot_date, datetime.time.max)
        local_dt_end_of_day = local_tz.localize(naive_end_of_day, is_dst=None)
        utc_dt_end_of_day = local_dt_end_of_day.astimezone(pytz.utc)
        snapshot_datetime_str = utc_dt_end_of_day.strftime('%Y-%m-%d %H:%M:%S')
        # --- End Timezone Handling ---

        # Base query parts - Fetch display names needed for the report
        base_query = """
            WITH LatestHistory AS (
                SELECT DISTINCT ON (h.product_id, h.location_id, h.lot_id, h.package_id)
                         h.product_id,
                         p.default_code,
                         pt.name as product_name,
                         h.location_id,
                         sl.complete_name as location_name,
                         h.lot_id,
                         lot.name as lot_name,
                         h.package_id,
                         pack.name as package_name,
                         h.quantity,
                         h.uom_id,
                         uom.name as uom_name,
                         h.user_id,
                         rp.name as user_name,
                         h.change_date
                FROM stock_quant_history h
                JOIN stock_location sl ON h.location_id = sl.id
                JOIN product_product p ON h.product_id = p.id
                JOIN product_template pt ON p.product_tmpl_id = pt.id
                LEFT JOIN stock_lot lot ON h.lot_id = lot.id
                LEFT JOIN stock_quant_package pack ON h.package_id = pack.id
                LEFT JOIN uom_uom uom ON h.uom_id = uom.id -- Assumes uom_id was added to history
                LEFT JOIN res_users ru ON h.user_id = ru.id
                LEFT JOIN res_partner rp ON ru.partner_id = rp.id
                WHERE h.change_date <= %(snapshot_time)s
                  AND sl.usage = 'internal'
                  AND pt.type != 'consu'
                  {where_filters} -- Placeholder for additional filters
                ORDER BY
                    h.product_id,
                    h.location_id,
                    h.lot_id,
                    h.package_id,
                    h.change_date DESC
            )
            -- Select from the latest records where quantity is not zero
            SELECT * FROM LatestHistory WHERE quantity > 0;
        """

        params = {'snapshot_time': snapshot_datetime_str}
        where_clauses = []

        # Add filters based on user input from the wizard record
        if report_wizard.product_filter_id:
            where_clauses.append("h.product_id = %(product_id)s")
            params['product_id'] = report_wizard.product_filter_id.id
        if report_wizard.location_filter_id:
            where_clauses.append("h.location_id = %(location_id)s")
            params['location_id'] = report_wizard.location_filter_id.id
        if report_wizard.lot_filter_id:
            where_clauses.append("h.lot_id = %(lot_id)s")
            params['lot_id'] = report_wizard.lot_filter_id.id

        where_filters_str = ""
        if where_clauses:
            where_filters_str = "AND " + " AND ".join(where_clauses)

        final_query = base_query.format(where_filters=where_filters_str)

        _logger.debug("Executing snapshot report query: %s with params: %s", final_query, params)
        try:
            self.env.cr.execute(final_query, params)
            results = self.env.cr.dictfetchall()
        except Exception as e:
            _logger.error("Error during snapshot report query execution. Query: %s Params: %s Error: %s", final_query, params, e)
            raise UserError(_("Failed to retrieve report data. Please check logs."))

        return results


    def generate_xlsx_report(self, workbook, data, objects):
        report_wizard = objects # Assuming only one wizard record triggers it
        report_wizard.ensure_one()
        snapshot_date = report_wizard.date_snapshot

        _logger.info(f"Generating XLSX report for wizard {report_wizard.id} on date {snapshot_date}")
        report_data = self._get_snapshot_data_for_report(report_wizard)
        _logger.info(f"Retrieved {len(report_data)} lines for the report.")

        sheet = workbook.add_worksheet(f'Inventory {snapshot_date.strftime("%Y-%m-%d")}')

        # --- Add Formats ---
        header_format = workbook.add_format({'bold': True, 'bg_color': '#A9A9A9', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        title_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter'})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss', 'align': 'left', 'border': 1})
        float_format = workbook.add_format({'num_format': '#,##0.00##', 'align': 'right', 'border': 1}) # Allow more decimal places if needed
        text_format = workbook.add_format({'border': 1, 'align': 'left'})
        text_wrap_format = workbook.add_format({'border': 1, 'align': 'left', 'text_wrap': True, 'valign': 'top'})

        # --- Write Title ---
        sheet.merge_range('A1:I1', f'Inventory Snapshot as of {snapshot_date.strftime("%Y-%m-%d")}', title_format) # Adjusted merge range
        sheet.set_row(0, 30) # Set title row height

        # --- Write Headers ---
        headers = [
            'Product Code', 'Product Name', 'Location', 'Lot/Serial', 'Package',
            'Quantity', 'UoM', 'Last Updated By', 'Last Update Date'
        ]
        # Adjusted range if title exists (start headers row 1, index 0)
        for col, header in enumerate(headers):
            sheet.write(1, col, header, header_format)

        # --- Set Column Widths ---
        sheet.set_column('A:A', 15)  # Product Code
        sheet.set_column('B:B', 35)  # Product Name
        sheet.set_column('C:C', 30)  # Location
        sheet.set_column('D:D', 20)  # Lot/Serial
        sheet.set_column('E:E', 20)  # Package
        sheet.set_column('F:F', 12)  # Quantity
        sheet.set_column('G:G', 10)  # UoM
        sheet.set_column('H:H', 20)  # Last Updated By
        sheet.set_column('I:I', 18)  # Last Update Date

        # --- Write Data Rows ---
        row = 2 # Start data below headers (index 2)
        user_tz = self.env.user.tz or 'UTC'
        local_tz = pytz.timezone(user_tz)

        if not report_data:
             _logger.warning("No data found to write to the XLSX report.")
             sheet.merge_range(f'A{row}:I{row}', 'No inventory found for the selected date and criteria.', text_format)
             return # Stop processing if no data

        for line_idx, line in enumerate(report_data):
            try:
                # --- Defensive String Conversion ---
                # Convert potentially complex types (like translation dicts or None) to simple strings for Excel
                product_code = str(line.get('default_code', ''))
                product_name = str(line.get('product_name', '')) # <-- Key change: ensure string
                location_name = str(line.get('location_name', ''))# <-- Key change: ensure string
                lot_name = str(line.get('lot_name', ''))        # <-- Key change: ensure string
                package_name = str(line.get('package_name', ''))# <-- Key change: ensure string
                uom_name = str(line.get('uom_name', ''))        # <-- Key change: ensure string
                user_name = str(line.get('user_name', ''))      # <-- Key change: ensure string
                quantity = line.get('quantity', 0.0) # Keep as float

                # --- Write cells using converted strings ---
                sheet.write(row, 0, product_code, text_format)
                sheet.write(row, 1, product_name, text_wrap_format) # Use converted string
                sheet.write(row, 2, location_name, text_wrap_format) # Use converted string
                sheet.write(row, 3, lot_name, text_format)           # Use converted string
                sheet.write(row, 4, package_name, text_format)       # Use converted string
                sheet.write(row, 5, quantity, float_format)          # Use original float
                sheet.write(row, 6, uom_name, text_format)           # Use converted string
                sheet.write(row, 7, user_name, text_format)         # Use converted string

                # Convert UTC change_date from DB back to user's timezone for display
                last_change_date_utc = line.get('change_date')
                if last_change_date_utc and isinstance(last_change_date_utc, datetime.datetime): # Add type check for safety
                    try:
                        # Ensure timezone aware before converting
                        if last_change_date_utc.tzinfo is None:
                             utc_dt = pytz.utc.localize(last_change_date_utc)
                        else:
                             utc_dt = last_change_date_utc.astimezone(pytz.utc) # Ensure it's UTC

                        local_dt = utc_dt.astimezone(local_tz)
                        # write_datetime expects naive datetime
                        sheet.write_datetime(row, 8, local_dt.replace(tzinfo=None), date_format)
                    except Exception as date_e:
                        _logger.warning(f"Could not convert date {last_change_date_utc} for row {row} (index {line_idx}): {date_e}", exc_info=True)
                        sheet.write(row, 8, str(last_change_date_utc), text_format) # Write as string if conversion fails
                else:
                    sheet.write(row, 8, '', text_format) # Write empty if no date or wrong type

                row += 1
            except Exception as write_e:
                 _logger.error(f"Error writing row {row} (data index {line_idx}) to XLSX: {write_e}\nData: {line}", exc_info=True)
                 # Optionally write an error placeholder in the sheet or just skip the row
                 try:
                     sheet.write(row, 0, f"Error processing row {line_idx+1}", text_format)
                     # You might want to skip incrementing 'row' here if you overwrite the error row later
                     row += 1
                 except Exception: # Ignore errors during error writing
                     pass
                 # Decide if you want to continue processing other rows or raise the error
                 # continue # Uncomment to try processing next row
                 # raise UserError(_("An error occurred while generating the report for some rows. Please check the logs.")) # Uncomment to stop

        # Optional: Freeze panes
        sheet.freeze_panes(2, 0) # Freeze title and header rows (Row 2 is the first data row)
        _logger.info(f"Finished writing {row - 2} data rows to XLSX.")
        



class ReportInventorySnapshotSummaryXlsx(models.AbstractModel):
    # The _name MUST match report_name in the new ir.actions.report XML definition
    _name = 'report.edge_module.report_inventory_snapshot_summary_xlsx' # *** CHECK MODULE NAME ***
    _description = 'Inventory Snapshot Summary XLSX Report Generator'
    _inherit = 'report.report_xlsx.abstract'

    def _get_snapshot_summary_data(self, report_wizard):
        """
        Helper method to run the query for summarized data based on the wizard's state.
        Groups by product and sums quantity. Includes cost.
        """
        snapshot_date = report_wizard.date_snapshot
        product_filter_id = report_wizard.product_filter_id
        location_filter_id = report_wizard.location_filter_id

        # --- Timezone Handling ---
        user_tz = self.env.user.tz or 'UTC'
        local_tz = pytz.timezone(user_tz)
        naive_end_of_day = datetime.datetime.combine(snapshot_date, datetime.time.max)
        local_dt_end_of_day = local_tz.localize(naive_end_of_day, is_dst=None)
        utc_dt_end_of_day = local_dt_end_of_day.astimezone(pytz.utc)
        snapshot_datetime_str = utc_dt_end_of_day.strftime('%Y-%m-%d %H:%M:%S')
        # --- End Timezone Handling ---

        # --- Get child locations if a parent location is selected ---
        location_ids = []
        if location_filter_id:
            location_ids = self.env['stock.location'].search([
                ('id', 'child_of', location_filter_id.id),
                ('usage', '=', 'internal')
            ]).ids
            if not location_ids: location_ids = [location_filter_id.id]
        # If no location filter, consider all internal locations

        # Summarized query: Group by product, sum quantity, get cost
        summary_query = """
            WITH LatestHistory AS (
                SELECT DISTINCT ON (h.product_id, h.location_id, h.lot_id, h.package_id)
                         h.product_id,
                         h.quantity
                FROM stock_quant_history h
                JOIN stock_location sl ON h.location_id = sl.id
                JOIN product_product p ON h.product_id = p.id
                JOIN product_template pt ON p.product_tmpl_id = pt.id
                WHERE h.change_date <= %(snapshot_time)s
                  AND sl.usage = 'internal'
                  AND pt.type != 'consu'
                  {where_filters} -- Apply product/location filters here
                ORDER BY
                    h.product_id, h.location_id, h.lot_id, h.package_id, h.change_date DESC
            )
            -- Aggregate the results from the latest states
            SELECT
                p.id as product_id,
                p.default_code,
                pt.name as product_name,
                SUM(lh.quantity) as total_quantity,
                pt.uom_id,
                uom.name as uom_name,
                COALESCE(pt.standard_price, 0.0) as cost_per_unit -- Use COALESCE for safety
            FROM LatestHistory lh
            JOIN product_product p ON lh.product_id = p.id
            JOIN product_template pt ON p.product_tmpl_id = pt.id
            JOIN uom_uom uom ON pt.uom_id = uom.id
            WHERE lh.quantity <> 0 -- Filter out zero quantity *latest* records before summing
            GROUP BY p.id, p.default_code, pt.name, pt.uom_id, uom.name, pt.standard_price
            HAVING SUM(lh.quantity) <> 0 -- Exclude products with zero total quantity
            ORDER BY p.default_code, pt.name;
        """

        params = {'snapshot_time': snapshot_datetime_str}
        where_clauses = []

        if product_filter_id:
            where_clauses.append("h.product_id = %(product_id)s")
            params['product_id'] = product_filter_id.id
        if location_ids: # Apply location filter if provided
            where_clauses.append("h.location_id = ANY(%(location_ids)s)")
            params['location_ids'] = location_ids

        where_filters_str = "AND " + " AND ".join(where_clauses) if where_clauses else ""
        final_query = summary_query.format(where_filters=where_filters_str)

        _logger.debug("Executing snapshot summary query: %s with params: %s", final_query, params)
        try:
            self.env.cr.execute(final_query, params)
            results = self.env.cr.dictfetchall()
        except Exception as e:
            _logger.error("Error during snapshot summary query execution: %s", e, exc_info=True)
            raise UserError(_("Failed to retrieve summary report data. Please check logs."))

        return results

    def generate_xlsx_report(self, workbook, data, objects):
        report_wizard = objects # Wizard record passed from action_export_summary_xlsx
        report_wizard.ensure_one()
        snapshot_date = report_wizard.date_snapshot

        _logger.info(f"Generating Summary XLSX report for wizard {report_wizard.id} on date {snapshot_date}")
        report_data = self._get_snapshot_summary_data(report_wizard)
        _logger.info(f"Retrieved {len(report_data)} summary lines for the report.")

        sheet = workbook.add_worksheet(f'Inv Summary {snapshot_date.strftime("%Y-%m-%d")}')

        # --- Add Formats ---
        title_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter'})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#A9A9A9', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        text_format = workbook.add_format({'border': 1, 'align': 'left'})
        text_wrap_format = workbook.add_format({'border': 1, 'align': 'left', 'text_wrap': True, 'valign': 'top'})
        float_format = workbook.add_format({'num_format': '#,##0.00##', 'align': 'right', 'border': 1})
        # Attempt to get company currency for formatting
        currency = report_wizard.company_id.currency_id or self.env.company.currency_id
        currency_format = workbook.add_format({'num_format': currency.excel_format or '#,##0.00', 'align': 'right', 'border': 1})

        # --- Write Title ---
        sheet.merge_range('A1:F1', f'Inventory Summary as of {snapshot_date.strftime("%Y-%m-%d")}', title_format)
        sheet.set_row(0, 30)

        # --- Write Headers ---
        headers = [
            'Internal Ref', 'Product Name', 'Total Quantity', 'UoM', 'Cost/Unit', 'Total Value'
        ]
        for col, header in enumerate(headers):
            sheet.write(1, col, header, header_format) # Start headers row 1 (index 1)

        # --- Set Column Widths ---
        sheet.set_column('A:A', 18)  # Internal Ref
        sheet.set_column('B:B', 40)  # Product Name
        sheet.set_column('C:C', 15)  # Total Quantity
        sheet.set_column('D:D', 10)  # UoM
        sheet.set_column('E:E', 15)  # Cost/Unit
        sheet.set_column('F:F', 18)  # Total Value

        # --- Write Data Rows ---
        row = 2 # Start data below headers (index 2)

        if not report_data:
             _logger.warning("No data found for summary report.")
             sheet.merge_range(f'A{row}:F{row}', 'No inventory summary data found for the selected date and criteria.', text_format)
             return

        grand_total_value = 0.0

        for line in report_data:
            try:
                # Extract data (using str() for text fields defensively)
                ref = str(line.get('default_code', ''))
                name = str(line.get('product_name', ''))
                qty = line.get('total_quantity', 0.0)
                uom = str(line.get('uom_name', ''))
                cost = line.get('cost_per_unit', 0.0) # COALESCE in SQL handles None
                total_value = qty * cost
                grand_total_value += total_value

                # Write row data
                sheet.write(row, 0, ref, text_format)
                sheet.write(row, 1, name, text_wrap_format)
                sheet.write(row, 2, qty, float_format)
                sheet.write(row, 3, uom, text_format)
                sheet.write(row, 4, cost, currency_format)
                sheet.write(row, 5, total_value, currency_format)

                row += 1
            except Exception as write_e:
                _logger.error(f"Error writing summary row {row} to XLSX: {write_e}\nData: {line}", exc_info=True)
                try:
                    sheet.write(row, 0, f"Error processing row", text_format)
                    row += 1
                except Exception: pass # Ignore error during error writing

        # --- Write Grand Total ---
        if grand_total_value > 0 or len(report_data) > 0 : # Write total row if there was data
             total_header_format = workbook.add_format({'bold': True, 'border': 1, 'align': 'right'})
             total_value_format = workbook.add_format({'bold': True, 'num_format': currency.excel_format or '#,##0.00', 'align': 'right', 'border': 1})
             sheet.merge_range(f'A{row}:E{row}', 'Grand Total:', total_header_format)
             sheet.write(row, 5, grand_total_value, total_value_format)


        # Optional: Freeze panes
        sheet.freeze_panes(2, 0) # Freeze title and header rows
        _logger.info(f"Finished writing {len(report_data)} summary rows to XLSX.")
