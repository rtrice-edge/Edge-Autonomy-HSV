# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import datetime
import pytz
import logging

_logger = logging.getLogger(__name__)

class InventorySnapshotReport(models.TransientModel):
    """
    Transient model to hold the date selection and display
    the calculated inventory snapshot lines. Includes filtering options.
    """
    _name = 'inventory.snapshot.report'
    _description = 'Inventory Snapshot Report Viewer'

    date_snapshot = fields.Date(
        string="Snapshot Date",
        required=True,
        default=lambda self: fields.Date.context_today(self),
        help="Date for the inventory snapshot.")

    # --- New Filter Fields ---
    product_filter_id = fields.Many2one(
        'product.product', string="Product Filter",
        help="Optional: Filter results for a specific product.")
    location_filter_id = fields.Many2one(
        'stock.location', string="Location Filter",
        domain=[('usage', '=', 'internal')], # Only allow filtering by internal locations
        help="Optional: Filter results for a specific internal location.")
    lot_filter_id = fields.Many2one(
        'stock.lot', string="Lot/Serial Filter",
        domain="[('product_id', '=?', product_filter_id)]", # Dynamic domain based on product
        help="Optional: Filter results for a specific Lot/Serial Number.")
    # --- End Filter Fields ---

    line_ids = fields.One2many(
        'inventory.snapshot.line',
        'report_id',
        string="Inventory Lines",
        readonly=True)

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company)

    def action_generate_snapshot(self):
        """ Button action to compute and display snapshot lines, applying filters. """
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
                    'type': 'info', # Use 'info' instead of 'warning' as it's expected sometimes
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

    def _get_inventory_snapshot_lines(self):
        """
        Calculates snapshot data, applying filters, and returns vals list.
        """
        self.ensure_one()
        snapshot_date = self.date_snapshot

        # --- Timezone Handling (same as before) ---
        user_tz = self.env.user.tz or 'UTC'
        local_tz = pytz.timezone(user_tz)
        naive_end_of_day = datetime.datetime.combine(snapshot_date, datetime.time.max)
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
            SELECT * FROM LatestHistory WHERE quantity > 0;
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

# --- Add action method to InventorySnapshotLine ---
class InventorySnapshotLine(models.TransientModel):
    _name = 'inventory.snapshot.line'
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
        action = {
            'name': _('History for %s') % (self.product_id.display_name),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.quant.history',
            'view_mode': 'tree,form',
            'views': [(False, 'tree'), (False, 'form')],
            'domain': domain,
            'target': 'current', # Open in main view or 'new' for dialog
            'context': { # Optional context, e.g., default search
                'search_default_product_id': self.product_id.id,
                'search_default_location_id': self.location_id.id,
                'search_default_lot_id': self.lot_id.id if self.lot_id else False,
            }
        }
        return action

