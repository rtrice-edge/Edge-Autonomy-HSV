# models/mrp_location_change.py
from odoo import models, fields, api
from odoo.exceptions import UserError

class MrpProductionLocationChange(models.Model):
    _name = 'mrp.production.location.change'
    _description = 'Manufacturing Order Location Change'
    _rec_name = 'production_id'
    _order = 'id desc'

    production_id = fields.Many2one('mrp.production', string='Manufacturing Order', required=True)
    location_src_id = fields.Many2one('stock.location', string='Source Location', required=True)
    location_dest_id = fields.Many2one('stock.location', string='Destination Location', required=True)
    date = fields.Datetime(string='Change Date', default=fields.Datetime.now, readonly=True)
    user_id = fields.Many2one('res.users', string='Changed By', default=lambda self: self.env.user, readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')
    ], string='Status', default='draft', readonly=True)
    
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
            production_location = self.env.ref('stock.location_production')
            
            # Update component moves (going to production)
            component_moves = production.move_raw_ids.filtered(
                lambda m: m.state not in ('done', 'cancel')
            )
            component_moves.write({
                'location_id': self.location_src_id.id,
                'location_dest_id': production_location.id,
            })

            # Update finished product moves (coming from production)
            finished_moves = production.move_finished_ids.filtered(
                lambda m: m.state not in ('done', 'cancel')
            )
            finished_moves.write({
                'location_id': production_location.id,
                'location_dest_id': self.location_dest_id.id,
            })
            
        self.write({'state': 'done'})
        return True