from odoo import models, fields, api
from odoo.exceptions import UserError

class HistoricalStockAdjustment(models.Model):
    _name = 'historical.stock.adjustment'
    _description = 'Historical Stock Adjustment'

    name = fields.Char(string='Adjustment Name', required=True)
    adjustment_date = fields.Date(string='Adjustment Date', required=True)
    adjustment_line_ids = fields.One2many(
        'historical.stock.adjustment.line', 'adjustment_id', string='Adjustment Lines'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')
    ], default='draft', string='State')

    def apply_adjustments(self):
        """Apply the inventory adjustments."""
        stock_move_obj = self.env['stock.move']
        for line in self.adjustment_line_ids:
            product = line.product_id
            location = line.location_id

            # If quantity is zero, create a log or dummy move for verification purposes
            if line.quantity == 0:
                move_vals = {
                    'name': f'Quantity Verified for {product.name}',
                    'product_id': product.id,
                    'product_uom_qty': 0,
                    'product_uom': product.uom_id.id,
                    'location_id': location.id,
                    'location_dest_id': location.id,
                    'date': line.adjustment_date,
                    'state': 'done',
                    'note': f'Quantity verified on {line.adjustment_date}. Note: {line.note or "No additional details"}',
                }
                stock_move_obj.create(move_vals)
            else:
                move_vals = {
                    'name': f'Historical Adjustment for {product.name}',
                    'product_id': product.id,
                    'product_uom_qty': abs(line.quantity),
                    'product_uom': product.uom_id.id,
                    'location_id': location.id if line.quantity < 0 else self.env.ref('stock.stock_location_adjustment').id,
                    'location_dest_id': location.id if line.quantity > 0 else self.env.ref('stock.stock_location_adjustment').id,
                    'date': line.adjustment_date,
                    'state': 'done',
                    'note': f'Quantity Changed on {line.adjustment_date}. Note: {line.note or "No additional details"}',
                }
                stock_move_obj.create(move_vals)

        self.state = 'done'
