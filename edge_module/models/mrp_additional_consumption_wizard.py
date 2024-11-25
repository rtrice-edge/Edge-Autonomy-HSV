# wizard/mrp_additional_consumption.py
from odoo import models, fields, api
from odoo.exceptions import UserError

class MrpAdditionalConsumptionWizard(models.TransientModel):
    _name = 'mrp.additional.consumption.wizard'
    _description = 'Additional Consumption Wizard'

    production_id = fields.Many2one('mrp.production', string='Manufacturing Order', required=True)
    line_ids = fields.One2many('mrp.additional.consumption.line.wizard', 'wizard_id', string='Consumption Lines')

    def action_add_consumption(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError('Please add at least one product to consume.')
        
        for line in self.line_ids:
            # Create stock move for consumption
            move_vals = {
                'name': f'Additional Consumption: {line.product_id.name}',
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.product_uom_id.id,
                'location_id': self.production_id.location_src_id.id,
                'location_dest_id': self.production_id.production_location_id.id,
                'raw_material_production_id': self.production_id.id,
                'origin': self.production_id.name,
                'state': 'confirmed',
            }
            move = self.env['stock.move'].create(move_vals)
            move._action_assign()
            move._set_quantity_done(line.quantity)
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

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id.id