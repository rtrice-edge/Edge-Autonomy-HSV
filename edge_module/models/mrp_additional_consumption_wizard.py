# models/mrp_production.p

# wizard/mrp_additional_consumption.py
from odoo import models, fields, api
from odoo.exceptions import UserError

class MrpAdditionalConsumptionWizard(models.TransientModel):
    _name = 'mrp.additional.consumption.wizard'
    _description = 'Additional Consumption Wizard'

    production_id = fields.Many2one('mrp.production', string='Manufacturing Order', required=True)
    location_src_id = fields.Many2one('stock.location', string='Source Location', required=True)
    line_ids = fields.One2many('mrp.additional.consumption.line.wizard', 'wizard_id', string='Consumption Lines')

    def action_add_consumption(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError('Please add at least one product to consume.')
        
        StockMove = self.env['stock.move']
        StockMoveLine = self.env['stock.move.line']
        
        for line in self.line_ids:
            if line.tracking != 'none' and not line.lot_id:
                raise UserError(f'Please specify lot/serial number for product {line.product_id.name}')

            # Create stock move
            move_vals = {
                'name': f'Additional Consumption: {line.product_id.name}',
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.product_uom_id.id,
                'location_id': self.location_src_id.id,
                'location_dest_id': self.production_id.production_location_id.id,
                'raw_material_production_id': self.production_id.id,
                'origin': self.production_id.name,
                'state': 'draft',
            }
            move = StockMove.create(move_vals)

            # Create stock move line with lot/serial if needed
            move_line_vals = {
                'move_id': move.id,
                'product_id': line.product_id.id,
                'product_uom_id': line.product_uom_id.id,
                'location_id': self.location_src_id.id,
                'location_dest_id': self.production_id.production_location_id.id,
                'qty_done': line.quantity,
            }
            
            if line.lot_id:
                move_line_vals.update({
                    'lot_id': line.lot_id.id,
                })
            
            StockMoveLine.create(move_line_vals)
            
            # Confirm and validate the move
            move._action_confirm()
            move._action_done()
        
        return {'type': 'ir.actions.act_window_close'}

class MrpAdditionalConsumptionLineWizard(models.TransientModel):
    _name = 'mrp.additional.consumption.line.wizard'
    _description = 'Additional Consumption Line Wizard'

    wizard_id = fields.Many2one('mrp.additional.consumption.wizard', string='Wizard Reference')
    product_id = fields.Many2one('product.product', string='Product', required=True,
                                domain="[('type', 'in', ['product', 'consu'])]")
    quantity = fields.Float('Quantity', required=True, default=1.0)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial Number',
                            domain="[('product_id', '=', product_id)]")
    tracking = fields.Selection(related='product_id.tracking', string='Tracking')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id.id
            self.lot_id = False