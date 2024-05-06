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



import logging
_logger = logging.getLogger(__name__)

#when a manufacturing order is confirmed, split the pick list into multiple pick lists based on the source location of the move lines

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

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
        production_ids = super()._split_productions(amounts, cancel_remaining_qty, set_consumed_qty)
        
        _logger.info("Original _split_productions function called")
        
        # Split the associated pickings
        for production in self:
            _logger.info(f"Processing production: {production.id}")
            pickings_to_split = production.picking_ids.filtered(lambda p: p.state not in ['done', 'cancel'])
            _logger.info(f"Pickings to split: {pickings_to_split}")
            
            for picking_index, picking in enumerate(pickings_to_split, start=1):
                _logger.info(f"Splitting picking: {picking.id}")
                new_picking_name = f"{picking.name}-{picking_index:03d}"
                new_picking = picking.copy({
                    'name': new_picking_name,
                    'move_ids': [],
                    'move_line_ids': [],
                    'backorder_id': picking.id,
                })
                _logger.info(f"New picking created: {new_picking.id} with name: {new_picking_name}")
                
                move_ids_to_split = picking.move_ids.filtered(lambda m: m.state not in ['done', 'cancel'])
                _logger.info(f"Move IDs to split: {move_ids_to_split}")
                
                for move in move_ids_to_split:
                    _logger.info(f"Splitting move: {move.id}")
                    new_move = move.copy({
                        'picking_id': new_picking.id,
                        'move_line_ids': [],
                    })
                    move.product_uom_qty = production.product_qty
                    new_move.product_uom_qty = production.product_qty
                    _logger.info(f"New move created: {new_move.id}")
                    
                    move_lines = move.move_line_ids.filtered(lambda ml: ml.state not in ['done', 'cancel'])
                    _logger.info(f"Move lines to process: {move_lines}")
                    
                    for move_line in move_lines:
                        _logger.info(f"Processing move line: {move_line.id}")
                        new_move_line = move_line.copy({
                            'picking_id': new_picking.id,
                            'move_id': new_move.id,
                        })
                        move_line.qty_done = production.product_qty
                        new_move_line.qty_done = production.product_qty
                        _logger.info(f"New move line created: {new_move_line.id}")
                
                new_picking.action_confirm()
                new_picking.action_assign()
                _logger.info(f"New picking confirmed and assigned: {new_picking.id}")
        
        _logger.info("Exiting _split_productions function")
        return self.env['mrp.production'].browse(production_ids)
