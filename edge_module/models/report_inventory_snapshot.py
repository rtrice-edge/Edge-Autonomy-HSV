# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import datetime
import pytz
import logging

_logger = logging.getLogger(__name__)

class ReportInventorySnapshotXlsx(models.AbstractModel):
    # The _name must match report_name in the ir.actions.report XML definition
    _name = 'report.edge_module.report_inventory_snapshot_xlsx' # Replace edge_module
    _description = 'Inventory Snapshot XLSX Report Generator'
    _inherit = 'report.report_xlsx.abstract'

    def _get_snapshot_data_for_report(self, report_wizard):
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
            -- Select from the latest records WITHOUT the quantity > 0 filter
            SELECT * FROM LatestHistory <> 0;
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

        self.env.cr.execute(final_query, params)
        results = self.env.cr.dictfetchall()
        return results


    def generate_xlsx_report(self, workbook, data, objects):
        # `objects` contains the wizard record(s) that triggered the report
        report_wizard = objects # Assuming only one wizard record triggers it
        report_wizard.ensure_one()
        snapshot_date = report_wizard.date_snapshot

        report_data = self._get_snapshot_data_for_report(report_wizard)

        sheet = workbook.add_worksheet(f'Inventory {snapshot_date.strftime("%Y-%m-%d")}')

        # --- Add Formats ---
        header_format = workbook.add_format({'bold': True, 'bg_color': '#A9A9A9', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        title_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter'})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss', 'align': 'left', 'border': 1})
        float_format = workbook.add_format({'num_format': '#,##0.00##', 'align': 'right', 'border': 1}) # Allow more decimal places if needed
        text_format = workbook.add_format({'border': 1, 'align': 'left'})
        text_wrap_format = workbook.add_format({'border': 1, 'align': 'left', 'text_wrap': True, 'valign': 'top'})

        # --- Write Title ---
        sheet.merge_range('A1:J1', f'Inventory Snapshot as of {snapshot_date.strftime("%Y-%m-%d")}', title_format)
        sheet.set_row(0, 30) # Set title row height

        # --- Write Headers ---
        headers = [
            'Product Code', 'Product Name', 'Location', 'Lot/Serial', 'Package',
            'Quantity', 'UoM', 'Last Updated By', 'Last Update Date'
        ]
        for col, header in enumerate(headers):
            # Adjust column index if title exists (start headers row 1)
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
        row = 2 # Start data below headers
        user_tz = self.env.user.tz or 'UTC'
        local_tz = pytz.timezone(user_tz)

        for line in report_data:
            sheet.write(row, 0, line.get('default_code', ''), text_format)
            sheet.write(row, 1, line.get('product_name', ''), text_wrap_format) # Allow wrap for long names
            sheet.write(row, 2, line.get('location_name', ''), text_wrap_format) # Allow wrap
            sheet.write(row, 3, line.get('lot_name', ''), text_format)
            sheet.write(row, 4, line.get('package_name', ''), text_format)
            sheet.write(row, 5, line.get('quantity', 0.0), float_format)
            sheet.write(row, 6, line.get('uom_name', ''), text_format)
            sheet.write(row, 7, line.get('user_name', ''), text_format)

            # Convert UTC change_date from DB back to user's timezone for display
            last_change_date_utc = line.get('change_date')
            if last_change_date_utc:
                 utc_dt = pytz.utc.localize(last_change_date_utc)
                 local_dt = utc_dt.astimezone(local_tz)
                 # write_datetime expects naive datetime
                 sheet.write_datetime(row, 8, local_dt.replace(tzinfo=None), date_format)
            else:
                 sheet.write(row, 8, '', text_format)

            row += 1

        # Optional: Freeze panes
        sheet.freeze_panes(2, 0) # Freeze title and header rows

