# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import datetime
import pytz # For timezone handling
import logging

_logger = logging.getLogger(__name__)

class InventorySnapshotReport(models.TransientModel):
    """
    Transient model to hold the date selection and display
    the calculated inventory snapshot lines.
    """
    _name = 'inventory.snapshot.report'
    _description = 'Inventory Snapshot Report Viewer'

    date_snapshot = fields.Date(
        string="Snapshot Date",
        required=True,
        # Default date based on current time - using context_today() is often cleaner
        default=lambda self: fields.Date.context_today(self),
        help="Date for the inventory snapshot.")

    line_ids = fields.One2many(
        'inventory.snapshot.line',
        'report_id',
        string="Inventory Lines",
        readonly=True) # Lines are computed, not manually added

 

    # Use a button instead of onchange for potentially long calculations
    def action_generate_snapshot(self):
        """ Button action to compute and display snapshot lines. """
        self.ensure_one()
        # Clear existing lines before generating new ones
        self.line_ids.unlink()
        lines_vals = self._get_inventory_snapshot_lines()
        if lines_vals:
            # Create the lines - linking them back via 'report_id' is done in _get_inventory_snapshot_lines
            self.env['inventory.snapshot.line'].create(lines_vals)
        else:
            # Optional: Show a notification if no data found
             return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Inventory Snapshot'),
                    'message': _('No inventory found for the selected date and criteria.'),
                    'sticky': False,
                    'type': 'warning',
                }
            }
        # Return action to refresh the view (or stay on the same view)
        # Returning the action ensures the view reloads with the new lines
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current', # Keep the user on the same view
        }


    def _get_inventory_snapshot_lines(self):
        """
        Calculates snapshot data and returns a list of value dictionaries
        ready for creating inventory.snapshot.line records.
        """
        self.ensure_one()
        snapshot_date = self.date_snapshot

        # --- Timezone Handling ---
        user_tz = self.env.user.tz or 'UTC' # Get user's timezone
        local_tz = pytz.timezone(user_tz)
        # Create datetime for end of the selected day in user's timezone
        naive_end_of_day = datetime.datetime.combine(snapshot_date, datetime.time.max)
        local_dt_end_of_day = local_tz.localize(naive_end_of_day, is_dst=None)
        # Convert this end-of-day time to UTC for database query
        utc_dt_end_of_day = local_dt_end_of_day.astimezone(pytz.utc)
        snapshot_datetime_str = utc_dt_end_of_day.strftime('%Y-%m-%d %H:%M:%S')
        # --- End Timezone Handling ---

        # Fetch data needed for lines, using SQL for DISTINCT ON performance
        query = """
            SELECT DISTINCT ON (h.product_id, h.location_id, h.lot_id, h.package_id)
                   h.product_id,
                   -- p.default_code, -- Not strictly needed for line creation, but could be added
                   -- pt.name as product_name, -- Not strictly needed
                   h.location_id,
                   -- sl.complete_name as location_name, -- Not strictly needed
                   h.lot_id,
                   -- lot.name as lot_name, -- Not strictly needed
                   h.quantity,
                   h.uom_id, -- Fetch UoM directly from history if added there
                   -- uom.name as uom_name, -- Not strictly needed
                   h.user_id,
                   -- rp.name as user_name, -- Not strictly needed
                   h.change_date,
                   h.package_id
            FROM stock_quant_history h
            JOIN stock_location sl ON h.location_id = sl.id
            -- Join other tables only if needed for filtering or data selection below
            -- JOIN product_product p ON h.product_id = p.id
            -- JOIN product_template pt ON p.product_tmpl_id = pt.id
            -- JOIN uom_uom uom ON h.uom_id = uom.id -- Join based on uom_id in history
            -- LEFT JOIN stock_lot lot ON h.lot_id = lot.id
            -- LEFT JOIN res_users ru ON h.user_id = ru.id
            -- LEFT JOIN res_partner rp ON ru.partner_id = rp.id
            WHERE h.change_date <= %(snapshot_time)s -- Use named placeholder
              AND sl.usage = 'internal'            -- Internal locations only
              AND h.quantity > 0                   -- Positive quantity only
             
            ORDER BY
                h.product_id,
                h.location_id,
                h.lot_id,          -- Ensure Lot ID is part of distinctness and ordering
                h.package_id,      -- Ensure Package ID is part of distinctness and ordering
                h.change_date DESC; -- Get the latest record within the distinct group
        """
        params = {
            'snapshot_time': snapshot_datetime_str,
         
            # commenting a comment.
        }
        self.env.cr.execute(query, params)
        results = self.env.cr.dictfetchall()

        lines_vals = []
        for res in results:
            lines_vals.append({
                'report_id': self.id, # Link back to the parent transient record
                'product_id': res['product_id'],
                'location_id': res['location_id'],
                'lot_id': res['lot_id'],
                'package_id': res['package_id'],
                'quantity': res['quantity'],
                'uom_id': res.get('uom_id'), # Use .get() in case uom_id wasn't added/fetched
                'last_updated_by': res['user_id'],
                'last_update_date': res['change_date'],
            })
        return lines_vals


class InventorySnapshotLine(models.TransientModel):
    """ Represents a single line in the Inventory Snapshot report (transient). """
    _name = 'inventory.snapshot.line'
    _description = 'Inventory Snapshot Report Line (Transient)'
    _order = 'location_id, product_id, lot_id' # Default sort order for lines

    report_id = fields.Many2one(
        'inventory.snapshot.report',
        ondelete='cascade', # Delete lines when the parent report record is deleted
        required=True,
        index=True)

    # --- Fields to display in the embedded tree view ---
    # Use related fields for better display names directly if needed,
    # but this can impact performance slightly vs simple IDs.
    # Simple IDs + view rendering is usually fine for transient models.

    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    location_id = fields.Many2one('stock.location', string='Location', readonly=True)
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial', readonly=True)
    package_id = fields.Many2one('stock.quant.package', string='Package', readonly=True)
    quantity = fields.Float(string='Quantity', digits='Product Unit of Measure', readonly=True)
    uom_id = fields.Many2one('uom.uom', string='UoM', readonly=True)
    last_updated_by = fields.Many2one('res.users', string='Last Updated By', readonly=True)
    last_update_date = fields.Datetime(string='Last Update Date', readonly=True)

    # --- Computed fields for display (alternative) ---
    # product_display_name = fields.Char(related='product_id.display_name', string='Product Name')
    # location_display_name = fields.Char(related='location_id.complete_name', string='Location Name')