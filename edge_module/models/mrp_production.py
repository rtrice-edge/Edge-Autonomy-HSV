from odoo import api, fields, models, _, Command

import logging
_logger = logging.getLogger(__name__)



class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    @api.multi
    def action_assign(self):
        res = super(MrpProduction, self).action_assign()
        for production in self:
            if production.state == 'confirmed':
                production.split_pick_list()
        return res

    def split_pick_list(self):
        for production in self:
            # Get the move lines associated with the manufacturing order
            move_lines = production.move_raw_ids

            # Create a dictionary to store the split move lines based on their source location
            split_moves = {}

            # Iterate over the move lines and split them based on their source location
            for move in move_lines:
                source_location = move.location_id
                if source_location not in split_moves:
                    split_moves[source_location] = []
                split_moves[source_location].append(move)

            # Create new pick lists for each split move group
            for location, moves in split_moves.items():
                # Create a new pick list
                picking = self.env['stock.picking'].create({
                    'picking_type_id': production.picking_type_id.id,
                    'location_id': location.id,
                    'location_dest_id': production.location_dest_id.id,
                    'origin': production.name,
                })

                # Move the split move lines to the new pick list
                moves.write({'picking_id': picking.id})

            # Update the state of the original pick list if all move lines have been split
            if not move_lines:
                production.picking_ids.write({'state': 'cancel'})