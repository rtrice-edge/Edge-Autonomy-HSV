import json
import datetime
import math
import re

from ast import literal_eval
from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _, Command
from odoo.addons.web.controllers.utils import clean_action
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_round, float_is_zero, format_datetime
from odoo.tools.misc import OrderedSet, format_date, groupby as tools_groupby
from math import ceil


import logging
_logger = logging.getLogger(__name__)

#when a manufacturing order is confirmed, split the pick list into multiple pick lists based on the source location of the move lines

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    @api.model
    def create(self, vals):
        production = super(MrpProduction, self).create(vals)
        production._update_bom_quantities()
        return production

    def _update_bom_quantities(self):
        for move in self.move_raw_ids:
            if move.product_uom.name == 'in':
                move.product_uom_qty = ceil(move.product_uom_qty)
        for move in self.move_finished_ids:
            if move.product_uom.name == 'in':
                move.product_uom_qty = ceil(move.product_uom_qty)



    def action_assign(self):
        res = super(MrpProduction, self).action_assign()
        for production in self:
            _logger.info(f'Checking if pick list should be split for MO {production.name}')
            if production.state == 'confirmed':
                _logger.info(f'MO {production.name} is confirmed, splitting pick list')
                production.split_pick_list()
        return res

    def split_pick_list(self):
        for production in self:
            _logger.info(f'Splitting pick list for MO {production.name}')
            # Get the move lines associated with the manufacturing order
            move_lines = production.move_raw_ids

            # Create a dictionary to store the split move lines based on their source location
            split_moves = {}

            # Iterate over the move lines and split them based on their source location
            for move in move_lines:
                _logger.info(f'Move {move.product_id.name} from {move.location_id.name} to {move.location_dest_id.name}')
                source_location = move.location_id
                if source_location not in split_moves:
                    split_moves[source_location] = []
                split_moves[source_location].append(move)

            # Create new pick lists for each split move group
            for location, moves in split_moves.items():
                # Create a new pick list
                _logger.info(f'Creating new pick list for location {location.name}')
                picking = self.env['stock.picking'].create({
                    'picking_type_id': production.picking_type_id.id,
                    'location_id': location.id,
                    'location_dest_id': production.location_dest_id.id,
                    'origin': production.name,
                })

                # Move the split move lines to the new pick list
                _logger.info(f'Moving {len(moves)} move lines to new pick list')
                moves.write({'picking_id': picking.id})

            # Update the state of the original pick list if all move lines have been split
            if not move_lines:
                _logger.info('All move lines have been split, setting original pick list to done')
                production.picking_ids.write({'state': 'cancel'})
    def _split_productions(self, amounts=False, cancel_remaining_qty=False, set_consumed_qty=False):
        _logger.info("Entering _split_productions function")
        
        # Call the original _split_productions function
        temp_value = super()._split_productions(amounts, cancel_remaining_qty, set_consumed_qty)
        
        _logger.info("Original _split_productions function called")
        
        # Split the associated pickings
        for production in self:
            _logger.info(f"Processing production: {production.id}")
            pickings_to_cancel = production.picking_ids.filtered(lambda p: p.state not in ['done', 'cancel'])
            _logger.info(f"Pickings to cancel: {pickings_to_cancel}")
            
            split_mos = production.procurement_group_id.mrp_production_ids.filtered(lambda mo: mo.backorder_sequence > 0)
            
            for picking in pickings_to_cancel:
                _logger.info(f"Cancelling picking: {picking.id}")
                picking.action_cancel()
                
                for split_mo in split_mos:
                    _logger.info(f"Creating new picking for split MO: {split_mo.id}")
                    pick_name = ""
                    if picking.picking_type_id.id == 6:
                        pick_name = "-PickList"
                    elif picking.picking_type_id.id == 7:
                        pick_name = "-PutAway"
                    new_picking = self.env['stock.picking'].create({
                        'name': split_mo.name + pick_name,
                        'origin': split_mo.name,
                        'picking_type_id': picking.picking_type_id.id,
                        'location_id': picking.location_id.id,
                        'location_dest_id': picking.location_dest_id.id,
                        'move_ids': [(0, 0, {
                            'name': move.name,
                            'product_id': move.product_id.id,
                            'product_uom': move.product_uom.id,
                            'product_uom_qty': split_mo.product_qty,
                            'location_id': move.location_id.id,
                            'location_dest_id': move.location_dest_id.id,
                            'origin': split_mo.name,
                        }) for move in picking.move_ids],
                    })
                    # Link the new picking to the split MO
                    # new_picking.production_id = split_mo.id
                    
                    _logger.info(f"New picking created: {new_picking.id}")
                    
                    new_picking.action_confirm()
                    new_picking.action_assign()
                    _logger.info(f"New picking confirmed and assigned: {new_picking.id}")
        
        _logger.info("Exiting _split_productions function")
        return temp_value
