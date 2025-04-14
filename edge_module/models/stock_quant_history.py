# -*- coding: utf-8 -*-

from odoo import models, fields, api

class StockQuantHistory(models.Model):
    _name = 'stock.quant.history'
    _description = 'Stock Quant History'
    _order = 'change_date desc, id desc' # Show newest first

    product_id = fields.Many2one(
        'product.product', 'Product',
        required=True, index=True, readonly=True)
    location_id = fields.Many2one(
        'stock.location', 'Location',
        required=True, index=True, readonly=True)
    lot_id = fields.Many2one(
        'stock.lot', 'Lot/Serial Number', index=True, readonly=True)
    package_id = fields.Many2one(
        'stock.quant.package', 'Package', index=True, readonly=True)

    quantity = fields.Float(
        'Quantity After Change', digits='Product Unit of Measure', readonly=True)
    uom_id = fields.Many2one(
        'uom.uom', string='Unit of Measure',
        related='product_id.uom_id', store=True, readonly=True) # store=True allows grouping/sorting
    

    change_date = fields.Datetime(
        'Change Date', required=True, default=fields.Datetime.now, index=True, readonly=True)
    user_id = fields.Many2one(
        'res.users', 'Updated By', default=lambda self: self.env.user, readonly=True)

    # Optional: Link to the move line or inventory adjustment that caused the change
    move_line_id = fields.Many2one('stock.move.line', 'Originating Move Line', readonly=True)
    #inventory_adjustment_id = fields.Many2one('stock.inventory', 'Originating Adjustment', readonly=True) # Or link to stock.quant if using direct adjustments

    _sql_constraints = [
        ('unique_quant_state_time', 'UNIQUE(product_id, location_id, lot_id, package_id, change_date, quantity, user_id)',
         'A history record for this exact state and time already exists.')
        # This constraint might be too strict if multiple operations happen within the same second by the same user.
        # Consider removing it if it causes issues, but it helps prevent pure duplicates from glitches.
    ]

    @api.depends('product_id', 'location_id', 'lot_id', 'quantity')
    def _compute_display_name(self):
        # Optional: Improve display name if needed
        for record in self:
            name = f"{record.product_id.display_name} @ {record.location_id.display_name}"
            if record.lot_id:
                name += f" [{record.lot_id.name}]"
            name += f": {record.quantity} ({record.change_date})"
            record.display_name = name