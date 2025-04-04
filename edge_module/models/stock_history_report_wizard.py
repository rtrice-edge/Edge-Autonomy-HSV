# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import datetime
import pytz
import logging

_logger = logging.getLogger(__name__)

class InventorySnapshotReport(models.TransientModel):
    _name = 'inventory.snapshot.report'
    _description = 'Inventory Snapshot Report Viewer'

    date_snapshot = fields.Date(
        string="Snapshot Date",
        required=True,
        default=lambda self: fields.Date.context_today(self),
        help="Date for the inventory snapshot.")

    product_filter_id = fields.Many2one(
        'product.product', string="Product Filter",
        help="Optional: Filter results for a specific product.")
    location_filter_id = fields.Many2one(
        'stock.location', string="Location Filter",
        domain=[('usage', '=', 'internal')],
        help="Optional: Filter results for a specific internal location.")
    lot_filter_id = fields.Many2one(
        'stock.lot', string="Lot/Serial Filter",
        domain="[('product_id', '=?', product_filter_id)]",
        help="Optional: Filter results for a specific Lot/Serial Number.")

    # line_ids field remains for the on-screen display triggered by action_generate_snapshot
    line_ids = fields.One2many(
        'inventory.snapshot.line',
        'report_id',
        string="Inventory Lines",
        readonly=True)

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company)

    def action_generate_snapshot(self):
        """ Button action to compute and display snapshot lines on screen """
        self.ensure_one()
        self.line_ids.unlink() # Clear previous results
        lines_vals = self._get_inventory_snapshot_lines() # Filters are applied inside this method
        if lines_vals:
            self.env['inventory.snapshot.line'].create(lines_vals)
        else:
             return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Inventory Snapshot'),
                    'message': _('No inventory found for the selected date and criteria.'),
                    'sticky': False,
                    'type': 'info',
                }
            }
        # Refresh the view
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # _get_inventory_snapshot_lines method remains unchanged (used by action_generate_snapshot)
    def _get_inventory_snapshot_lines(self):
        # ... (Keep the existing code from snapshot_report_model_py_neg_fix artifact) ...
        # --- Timezone Handling (same as before) ---
        user_tz = self.env.user.tz or 'UTC'
        local_tz = pytz.timezone(user_tz)
        naive_end_of_day = datetime.datetime.combine(self.date_snapshot, datetime.time.max)
        local_dt_end_of_day = local_tz.localize(naive_end_of_day, is_dst=None)
        utc_dt_end_of_day = local_dt_end_of_day.astimezone(pytz.utc)
        snapshot_datetime_str = utc_dt_end_of_day.strftime('%Y-%m-%d %H:%M:%S')
        # --- End Timezone Handling ---

        # Base query parts
        base_query = """
            WITH LatestHistory AS (
                SELECT DISTINCT ON (h.product_id, h.location_id, h.lot_id, h.package_id)
                       h.product_id,
                       h.location_id,
                       h.lot_id,
                       h.package_id,
                       h.quantity,
                       h.uom_id,
                       h.user_id,
                       h.change_date
                FROM stock_quant_history h
                JOIN stock_location sl ON h.location_id = sl.id
                JOIN product_product p ON h.product_id = p.id
                JOIN product_template pt ON p.product_tmpl_id = pt.id
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
            SELECT * FROM LatestHistory != 0;
            -- REMOVED: WHERE quantity > 0;
        """

        params = {'snapshot_time': snapshot_datetime_str}
        where_clauses = []

        # Add filters based on user input
        if self.product_filter_id:
            where_clauses.append("h.product_id = %(product_id)s")
            params['product_id'] = self.product_filter_id.id
        if self.location_filter_id:
            where_clauses.append("h.location_id = %(location_id)s")
            params['location_id'] = self.location_filter_id.id
        if self.lot_filter_id:
            where_clauses.append("h.lot_id = %(lot_id)s")
            params['lot_id'] = self.lot_filter_id.id

        # Construct the final WHERE clause string
        where_filters_str = ""
        if where_clauses:
            where_filters_str = "AND " + " AND ".join(where_clauses)

        # Inject the filters into the base query
        final_query = base_query.format(where_filters=where_filters_str)

        _logger.debug("Executing snapshot query: %s with params: %s", final_query, params)
        try:
            self.env.cr.execute(final_query, params)
            results = self.env.cr.dictfetchall()
        except Exception as e:
             _logger.error("Error during snapshot query execution. Query: %s Params: %s Error: %s", final_query, params, e)
             raise

        lines_vals = []
        for res in results:
            lines_vals.append({
                'report_id': self.id,
                'product_id': res['product_id'],
                'location_id': res['location_id'],
                'lot_id': res['lot_id'],
                'package_id': res['package_id'],
                'quantity': res['quantity'],
                'uom_id': res.get('uom_id'),
                'last_updated_by': res['user_id'],
                'last_update_date': res['change_date'],
            })
        return lines_vals

    # --- New Method for Export Button ---
    def action_export_xlsx(self):
        """ Button action to trigger the XLSX report download. """
        self.ensure_one()
        # Prepare data to pass to the report template if needed
        # The report can also access self (the wizard record) directly
        data = {
            'wizard_id': self.id,
            'date_snapshot': self.date_snapshot.strftime('%Y-%m-%d'),
            'product_filter_id': self.product_filter_id.id,
            'location_filter_id': self.location_filter_id.id,
            'lot_filter_id': self.lot_filter_id.id,
        }
        # Replace 'edge_module.action_report_inventory_snapshot'
        # with the actual XML ID of your ir.actions.report record
        report_action_ref = 'edge_module.action_report_inventory_snapshot'
        _logger.info(f"Triggering XLSX report action {report_action_ref} for date {self.date_snapshot} with filters")
        return self.env.ref(report_action_ref).report_action(self, data=data)


# InventorySnapshotLine class remains unchanged (used by action_generate_snapshot)
class InventorySnapshotLine(models.TransientModel):
    _name = 'inventory.snapshot.line'
    # ... (Keep the existing code from snapshot_report_model_py_neg_fix artifact) ...
    _description = 'Inventory Snapshot Report Line (Transient)'
    _order = 'location_id, product_id, lot_id'

    report_id = fields.Many2one(
        'inventory.snapshot.report',
        ondelete='cascade',
        required=True,
        index=True)

    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    location_id = fields.Many2one('stock.location', string='Location', readonly=True)
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial', readonly=True)
    package_id = fields.Many2one('stock.quant.package', string='Package', readonly=True)
    quantity = fields.Float(string='Quantity', digits='Product Unit of Measure', readonly=True)
    uom_id = fields.Many2one('uom.uom', string='UoM', readonly=True)
    last_updated_by = fields.Many2one('res.users', string='Last Updated By', readonly=True)
    last_update_date = fields.Datetime(string='Last Update Date', readonly=True)

    def action_view_history(self):
        """
        Returns an action to open the stock.quant.history records
        filtered for the specific item represented by this line.
        """
        self.ensure_one()
        domain = [
            ('product_id', '=', self.product_id.id),
            ('location_id', '=', self.location_id.id),
            ('lot_id', '=', self.lot_id.id), # Handles None correctly
            ('package_id', '=', self.package_id.id) # Handles None correctly
        ]
        # Add ordering to see the most recent history first
        action = {
            'name': _('History for %s') % (self.product_id.display_name),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.quant.history',
            'view_mode': 'tree,form',
            'views': [(False, 'tree'), (False, 'form')],
            'domain': domain,
            'target': 'current', # Open in main view or 'new' for dialog
            'context': {
                'search_default_product_id': self.product_id.id,
                'search_default_location_id': self.location_id.id,
                'search_default_lot_id': self.lot_id.id if self.lot_id else False,
                'search_default_group_by_location': 0, # Remove default grouping if any
                'search_default_group_by_product': 0,
            }
        }
        return action

