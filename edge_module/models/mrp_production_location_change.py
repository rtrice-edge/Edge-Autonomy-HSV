from odoo import models, fields, api
from odoo.exceptions import UserError

class ManufacturingProductionLocationChange(models.TransientModel):
    _name = 'mrp.production.location.change'
    _description = 'Manufacturing Production Location Change'

    production_id = fields.Many2one('mrp.production', string='Manufacturing Order', required=True)
    location_src_id = fields.Many2one('stock.location', string='Source Location', required=True)
    location_dest_id = fields.Many2one('stock.location', string='Destination Location', required=True)

    def action_change_locations(self):
        self.ensure_one()
        production = self.production_id
        
        # Only allow changes for draft and confirmed states
        if production.state not in ('draft', 'confirmed'):
            raise UserError('Location changes are only allowed for manufacturing orders in draft or confirmed state.')
            
        # Update MO locations
        production.write({
            'location_src_id': self.location_src_id.id,
            'location_dest_id': self.location_dest_id.id,
        })
        
        # Update location_id for stock moves associated with the manufacturing order
        for move in production.move_raw_ids:
            move.location_id = self.location_src_id.id
        
        return {'type': 'ir.actions.act_window_close'}