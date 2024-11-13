from odoo import models, fields, api

class ManufacturingProductionLocationChange(models.TransientModel):
    _name = 'mrp.production.location.change'
    _description = 'Manufacturing Production Location Change'

    mo_id = fields.Many2one('mrp.production', string='Manufacturing Order', required=True)
    location_src_id = fields.Many2one('stock.location', string='Source Location', required=True)
    location_dest_id = fields.Many2one('stock.location', string='Destination Location', required=True)

    def action_change_locations(self):
        view_id = self.env.ref('your_module.view_manufacturing_order_location_change_form').id
        return {
            'name': 'Change Manufacturing Order Locations',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'manufacturing.order.location.change',
            'views': [(view_id, 'form')],
            'target': 'new',
            'context': {
                'default_mo_id': self.id,
                'default_location_src_id': self.location_src_id.id,
                'default_location_dest_id': self.location_dest_id.id,
            }
        }