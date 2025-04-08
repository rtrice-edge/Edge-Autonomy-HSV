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
    _name = 'report.edge_module.report_inventory_snapshot_summary_xlsx' # *** CHECK MODULE NAME ***
    _description = 'Inventory Snapshot Summary XLSX Report Generator (by Product/Location)'
    _inherit = 'report.report_xlsx.abstract'

    def _get_snapshot_summary_data(self, report_wizard):
        """
        Helper method using SQL for aggregation (by product/location)
        and ORM for product/location details & cost.
        """
        snapshot_date = report_wizard.date_snapshot
        product_filter_id = report_wizard.product_filter_id
        location_filter_id = report_wizard.location_filter_id # Use the original filter ID

        # --- Timezone Handling ---
        user_tz = self.env.user.tz or 'UTC'
        local_tz = pytz.timezone(user_tz)
        naive_end_of_day = datetime.datetime.combine(snapshot_date, datetime.time.max)
        local_dt_end_of_day = local_tz.localize(naive_end_of_day, is_dst=None)
        utc_dt_end_of_day = local_dt_end_of_day.astimezone(pytz.utc)
        snapshot_datetime_str = utc_dt_end_of_day.strftime('%Y-%m-%d %H:%M:%S')
        # --- End Timezone Handling ---

        # --- Get child locations ---
        # location_ids will contain the specific locations to consider based on the filter
        location_ids_to_filter = []
        if location_filter_id:
            location_ids_to_filter = self.env['stock.location'].search([
                ('id', 'child_of', location_filter_id.id),
                ('usage', '=', 'internal')
            ]).ids
            if not location_ids_to_filter:
                _logger.warning(f"Location filter {location_filter_id.display_name} has no internal child locations.")
                # Depending on desired behavior, you might return empty or just use the parent ID
                return [] # Return empty if filter yields no locations
        # If no location_filter_id, location_ids_to_filter remains empty, and the SQL won't filter by specific location IDs.

        # --- Modified SQL Query for Aggregation by Product/Location ---
        summary_query = """
            WITH LatestHistory AS (
                -- Select product_id, location_id, and quantity for latest records
                SELECT DISTINCT ON (h.product_id, h.location_id, h.lot_id, h.package_id)
                         h.product_id,
                         h.location_id, -- Need location_id for grouping
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
            -- Aggregate quantities per product per location
            SELECT
                lh.product_id,
                lh.location_id, -- Select location_id
                SUM(lh.quantity) as total_quantity
            FROM LatestHistory lh
            -- No need to join product/location tables here, just need IDs
            WHERE lh.quantity <> 0
            GROUP BY lh.product_id, lh.location_id -- Group by both product and location
            HAVING SUM(lh.quantity) <> 0; -- Exclude combinations with zero total quantity
        """
        # --- End Modified SQL Query ---

        params = {'snapshot_time': snapshot_datetime_str}
        where_clauses = []

        if product_filter_id:
            where_clauses.append("h.product_id = %(product_id)s")
            params['product_id'] = product_filter_id.id
        # Apply location filter using the list derived earlier
        if location_ids_to_filter:
            where_clauses.append("h.location_id = ANY(%(location_ids)s)")
            params['location_ids'] = location_ids_to_filter

        where_filters_str = "AND " + " AND ".join(where_clauses) if where_clauses else ""
        final_query = summary_query.format(where_filters=where_filters_str)

        _logger.debug("Executing snapshot summary aggregation query (by P/L): %s with params: %s", final_query, params)
        try:
            self.env.cr.execute(final_query, params)
            # Results contain [{'product_id': id, 'location_id': id, 'total_quantity': qty}, ...]
            aggregation_results = self.env.cr.dictfetchall()
        except Exception as e:
            _logger.error("Error during snapshot summary aggregation query (by P/L): %s", e, exc_info=True)
            raise UserError(_("Failed to retrieve summary aggregation data. Please check logs."))

        if not aggregation_results:
            _logger.info("No aggregation results found for the summary report (by P/L).")
            return []

        # --- ORM Fetching and Data Combination (Products and Locations) ---
        product_ids = list(set(res['product_id'] for res in aggregation_results))
        location_ids = list(set(res['location_id'] for res in aggregation_results))

        # Create a map for quick lookup of quantity by (product_id, location_id) tuple
        quantity_map = {(res['product_id'], res['location_id']): res['total_quantity'] for res in aggregation_results}

        # Fetch product and location records using ORM
        _logger.debug(f"Fetching details via ORM for {len(product_ids)} products and {len(location_ids)} locations.")
        company_id = report_wizard.company_id.id or self.env.company.id
        products = self.env['product.product'].with_context(company_id=company_id).browse(product_ids)
        locations = self.env['stock.location'].browse(location_ids)

        # Create maps for quick lookup of objects by ID
        product_map = {prod.id: prod for prod in products}
        location_map = {loc.id: loc for loc in locations}

        final_data = []
        # Iterate through the original aggregation results to preserve the combinations
        for res in aggregation_results:
            product_id = res['product_id']
            location_id = res['location_id']
            total_quantity = res['total_quantity'] # Already summed per P/L

            product = product_map.get(product_id)
            location = location_map.get(location_id)

            if not product or not location:
                _logger.warning(f"Skipping row due to missing product ({product_id}) or location ({location_id}) in ORM results.")
                continue

            try:
                # Get cost via ORM
                cost_per_unit = product.standard_price
                # Get other details
                default_code = product.default_code or ''
                product_name = product.name or ''
                uom_name = product.uom_id.name or ''
                location_name = location.display_name or '' # Use display_name for locations

                final_data.append({
                    'product_id': product.id,
                    'location_id': location.id,
                    'default_code': default_code,
                    'product_name': product_name,
                    'location_name': location_name, # Add location name
                    'total_quantity': total_quantity,
                    'uom_name': uom_name,
                    'cost_per_unit': cost_per_unit,
                })
            except Exception as orm_e:
                _logger.error(f"Error processing P/L combo ({product_id}/{location_id}) via ORM: {orm_e}", exc_info=True)

        # Sort the final data (e.g., by location then product code)
        final_data.sort(key=lambda x: (x.get('location_name', ''), x.get('default_code', '')))

        _logger.info(f"Prepared {len(final_data)} lines for summary report (by P/L) after ORM processing.")
        return final_data

    # --- generate_xlsx_report method needs updates for the new column ---
    def generate_xlsx_report(self, workbook, data, objects):
        report_wizard = objects
        report_wizard.ensure_one()
        snapshot_date = report_wizard.date_snapshot

        _logger.info(f"Generating Summary XLSX report (by P/L) for wizard {report_wizard.id} on date {snapshot_date}")
        report_data = self._get_snapshot_summary_data(report_wizard)
        _logger.info(f"Received {len(report_data)} processed summary lines (by P/L) for the report.")

        sheet = workbook.add_worksheet(f'Inv Sum By Loc {snapshot_date.strftime("%Y-%m-%d")}') # Changed sheet name

        # --- Add Formats ---
        title_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter'})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#A9A9A9', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        text_format = workbook.add_format({'border': 1, 'align': 'left'})
        text_wrap_format = workbook.add_format({'border': 1, 'align': 'left', 'text_wrap': True, 'valign': 'top'})
        float_format = workbook.add_format({'num_format': '#,##0.00##', 'align': 'right', 'border': 1})
        # --- Currency Formatting (same as before) ---
        currency = report_wizard.company_id.currency_id or self.env.company.currency_id
        excel_num_format = '#,##0.00' # Default format
        if currency:
            decimal_places = currency.decimal_places
            excel_num_format = f"#,##0.{'0' * decimal_places}" if decimal_places > 0 else "#,##0"
        currency_format = workbook.add_format({'num_format': excel_num_format, 'align': 'right', 'border': 1})
        total_value_format = workbook.add_format({'bold': True, 'num_format': excel_num_format, 'align': 'right', 'border': 1})
        # --- End Currency Formatting ---

        # --- Write Title ---
        # *** Adjusted merge range for new column ***
        sheet.merge_range('A1:G1', f'Inventory Summary by Location as of {snapshot_date.strftime("%Y-%m-%d")}', title_format)
        sheet.set_row(0, 30)

        # --- Write Headers (Added Location) ---
        headers = [
            'Location', 'Internal Ref', 'Product Name', 'Total Quantity', 'UoM', 'Cost/Unit', 'Total Value'
        ]
        for col, header in enumerate(headers):
            sheet.write(1, col, header, header_format)

        # --- Set Column Widths (Adjusted for Location) ---
        sheet.set_column('A:A', 30)  # Location Name
        sheet.set_column('B:B', 18)  # Internal Ref
        sheet.set_column('C:C', 40)  # Product Name
        sheet.set_column('D:D', 15)  # Total Quantity
        sheet.set_column('E:E', 10)  # UoM
        sheet.set_column('F:F', 15)  # Cost/Unit
        sheet.set_column('G:G', 18)  # Total Value

        # --- Write Data Rows ---
        row = 2
        grand_total_value = 0.0
        if not report_data:
             _logger.warning("No data found for summary report (by P/L).")
             # *** Adjusted merge range ***
             sheet.merge_range(f'A{row}:G{row}', 'No inventory summary data found for the selected date and criteria.', text_format)
        else:
            for line in report_data: # Iterating through the final_data list
                try:
                    # Extract data including location_name
                    loc_name = str(line.get('location_name', '')) # Get Location Name
                    ref = str(line.get('default_code', ''))
                    name = str(line.get('product_name', ''))
                    qty = line.get('total_quantity', 0.0)
                    uom = str(line.get('uom_name', ''))
                    cost = line.get('cost_per_unit', 0.0)
                    total_value = qty * cost
                    grand_total_value += total_value

                    # Write row data (shifted columns after adding Location)
                    sheet.write(row, 0, loc_name, text_wrap_format) # Location in Col A
                    sheet.write(row, 1, ref, text_format)           # Ref in Col B
                    sheet.write(row, 2, name, text_wrap_format)     # Name in Col C
                    sheet.write(row, 3, qty, float_format)          # Qty in Col D
                    sheet.write(row, 4, uom, text_format)           # UoM in Col E
                    sheet.write(row, 5, cost, currency_format)      # Cost in Col F
                    sheet.write(row, 6, total_value, currency_format)# Value in Col G
                    row += 1
                except Exception as write_e:
                    _logger.error(f"Error writing summary row {row} to XLSX (by P/L): {write_e}\nData: {line}", exc_info=True)
                    try:
                        sheet.write(row, 0, f"Error processing row", text_format); row += 1
                    except Exception: pass

            # --- Write Grand Total ---
            # *** Adjusted merge range and column index ***
            if grand_total_value > 0 or len(report_data) > 0:
                 total_header_format = workbook.add_format({'bold': True, 'border': 1, 'align': 'right'})
                 # total_value_format already defined above
                 sheet.merge_range(f'A{row}:F{row}', 'Grand Total:', total_header_format) # Merge A to F
                 sheet.write(row, 6, grand_total_value, total_value_format) # Write value in Col G

        # Optional: Freeze panes
        sheet.freeze_panes(2, 0)
        _logger.info(f"Finished writing {len(report_data)} summary rows (by P/L) to XLSX.")

