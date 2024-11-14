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
        
        if production.state in ('done', 'cancel'):
            raise UserError('Cannot change locations of completed or cancelled manufacturing orders.')
            
        # Update MO locations
        production.write({
            'location_src_id': self.location_src_id.id,
            'location_dest_id': self.location_dest_id.id,
        })

        # Update stock moves if MO is in progress
        if production.state not in ('draft'):
            # Get the production location
            production_location = self.env['stock.location'].search([
                ('usage', '=', 'production')
            ], limit=1)
            
            if not production_location:
                raise UserError('Production location not found in the system.')
            
            # Update component moves (going to production)
            component_moves = production.move_raw_ids.filtered(
                lambda m: m.state not in ('done', 'cancel')
            )
            if component_moves:
                component_moves.write({
                    'location_id': self.location_src_id.id,
                    'location_dest_id': production_location.id,
                })

            # Update finished product moves (coming from production)
            finished_moves = production.move_finished_ids.filtered(
                lambda m: m.state not in ('done', 'cancel')
            )
            if finished_moves:
                finished_moves.write({
                    'location_id': production_location.id,
                    'location_dest_id': self.location_dest_id.id,
                })
            
        return {'type': 'ir.actions.act_window_close'}