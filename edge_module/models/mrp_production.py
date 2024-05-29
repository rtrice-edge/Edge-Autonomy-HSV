import json
import datetime
import math
import re

from ast import literal_eval
from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.addons.web.controllers.utils import clean_action
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_round, float_is_zero, format_datetime
from odoo.tools.misc import OrderedSet, format_date, groupby as tools_groupby
from math import ceil
from odoo import models, fields, api
from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    mrp_productions = env['mrp.production'].search([('planned_week', '=', False)])
    mrp_productions.write({'planned_week': 'unplanned'})


#when a manufacturing order is confirmed, split the pick list into multiple pick lists based on the source location of the move lines

class MrpProduction(models.Model):
    _inherit = 'mrp.production'
    alias = fields.Char(string='Alias', compute='_compute_alias', store=False,
                        help='Helps to identify the MO in the system')
    planned_week = fields.Selection(selection=[
        ('this_week', 'This Week'),
        ('next_week', 'Next Week'),
        ('two_weeks', '2 Weeks from Now'),
        ('unplanned', 'Unplanned')
    ], string='Planned Week', default='unplanned')
  
    def change_planned_week(self, new_planned_week):
        self.write({'planned_week': new_planned_week})
    
    
    @api.depends('name', 'product_id.default_code')
    def _compute_alias(self):
        for production in self:
            if production.name and production.product_id.default_code:
                production.alias = f"{production.name}-[{production.product_id.default_code}]"
            else:
                production.alias = False

    # def _update_bom_quantities(self):
    #     for move in self.move_raw_ids:
    #         if move.product_uom.name == 'in':
    #             move.product_uom_qty = ceil(move.product_uom_qty)
    #     for move in self.move_finished_ids:
    #         if move.product_uom.name == 'in':
    #             move.product_uom_qty = ceil(move.product_uom_qty)



    # def action_assign(self):
    #     # res = super(MrpProduction, self).action_assign()
    #     # for production in self:
    #     #     _logger.info(f'Checking if pick list should be split for MO {production.name}')
    #     #     if production.state == 'confirmed':
    #     #         _logger.info(f'MO {production.name} is confirmed, splitting pick list')
    #     #         production.split_pick_list()
    #     # return res

    # def split_pick_list(self):
    #     for production in self:
    #         _logger.info(f'Splitting pick list for MO {production.name}')
    #         # Get the move lines associated with the manufacturing order
    #         move_lines = production.move_raw_ids

    #         # Create a dictionary to store the split move lines based on their source location
    #         split_moves = {}

    #         # Iterate over the move lines and split them based on their source location
    #         for move in move_lines:
    #             _logger.info(f'Move {move.product_id.name} from {move.location_id.name} to {move.location_dest_id.name}')
    #             source_location = move.location_id
    #             if source_location not in split_moves:
    #                 split_moves[source_location] = []
    #             split_moves[source_location].append(move)

    #         # Create new pick lists for each split move group
    #         for location, moves in split_moves.items():
    #             # Create a new pick list
    #             _logger.info(f'Creating new pick list for location {location.name}')
    #             picking = self.env['stock.picking'].create({
    #                 'picking_type_id': production.picking_type_id.id,
    #                 'location_id': location.id,
    #                 'location_dest_id': production.location_dest_id.id,
    #                 'origin': production.name,
    #             })

    #             # Move the split move lines to the new pick list
    #             _logger.info(f'Moving {len(moves)} move lines to new pick list')
    #             moves.write({'picking_id': picking.id})

    #         # Update the state of the original pick list if all move lines have been split
    #         if not move_lines:
    #             _logger.info('All move lines have been split, setting original pick list to done')
    #             production.picking_ids.write({'state': 'cancel'})
    # def _split_productions(self, amounts=False, cancel_remaining_qty=False, set_consumed_qty=False):
    #     _logger.info("Entering _split_productions function")
    #     production_ids = super()._split_productions(amounts, cancel_remaining_qty, set_consumed_qty)

    #     # Get the split MO records
    #     split_mo_ids = production_ids.ids
    #     split_mos = self.env['mrp.production'].search([('id', 'in', split_mo_ids)])
    #     _logger.info(f"Split MOs: {split_mos}")
    #     for production in self:
    #         _logger.info(f"Processing production: {production.id}")
    #         pickings_to_cancel = production.picking_ids.filtered(lambda p: p.state not in ['done', 'cancel'])
            
    #         _logger.info(f"Pickings to cancel: {pickings_to_cancel}")
    #         for picking in pickings_to_cancel:
    #             _logger.info(f"examining picking: {picking.id} {picking.name} {picking.picking_type_id.id}")
    #             if picking.picking_type_id.id not in [6, 7]:
    #                 _logger.info(f"not cancelling picking: {picking.id} {picking.name}")
    #                 continue
    #             picking.action_cancel()
                
    #             for split_mo in split_mos:
    #                 #procurement_group_id = self.get_procurement_group(split_mo.procurement_group_id.name)
    #                 _logger.info(f"Creating new picking for split MO: {split_mo.id} {split_mo.name}")
    #                 _logger.info(f"Picking type: {picking.picking_type_id.id}")
    #                 pick_name = ""
    #                 if picking.picking_type_id.id == 6:
    #                     pick_name = split_mo.name+ "-PickList"
    #                 elif picking.picking_type_id.id == 7:
    #                     pick_name = split_mo.name+ "-PutAway"
    #                 _logger.info(f"Pick Name: {pick_name}")
    #                 group_id = self.get_procurement_group(split_mo.name)
    #                 stock_moves = split_mo.move_raw_ids | split_mo.move_finished_ids
    #                 new_picking = self.env['stock.picking'].create({
    #                     'name': pick_name,
    #                     'picking_type_id': picking.picking_type_id.id,
    #                     'location_id': picking.location_id.id,
    #                     'location_dest_id': picking.location_dest_id.id,
    #                     'origin': split_mo.name,
    #                     'group_id': group_id,
    #                     'move_ids': [(6, 0, stock_moves.ids)],
    #                 })

    #                 _logger.info(f"New picking created: {new_picking.id}")
                    
    #                 new_picking.action_confirm()
    #                 _logger.info(f"New picking confirmed: {new_picking.id}")
    #                 new_picking.action_assign()
    #                 _logger.info(f"New picking confirmed and assigned: {new_picking.id}")
        
    #     _logger.info("Exiting _split_productions function")
    #     return production_ids
    
    def get_procurement_group(self, group_name):
        procurement_group_name = group_name
        procurement_group = self.env['procurement.group'].search([('name', '=', procurement_group_name)])
        if not procurement_group:
            _logger.info("Procurement Group not found, creating new one...")
            procurement_group = self.env['procurement.group'].create({'name': procurement_group_name})
            _logger.info(f"New Procurement Group created: {procurement_group}")
            
        group_id = procurement_group.id
        return group_id
    # def _split_productions(self, amounts=False, cancel_remaining_qty=False, set_consumed_qty=False):
    #     _logger.info("Entering _split_productions function")
    #     production_ids = super()._split_productions(amounts, cancel_remaining_qty, set_consumed_qty)
        
    #     # Get the split MO records
    #     split_mo_ids = production_ids.ids
    #     split_mos = self.env['mrp.production'].search([('id', 'in', split_mo_ids)])
    #     _logger.info(f"Split MOs: {split_mos}")
        
    #     for production in self:
    #         _logger.info(f"Processing production: {production.id}")
    #         pickings_to_cancel = production.picking_ids.filtered(lambda p: p.state not in ['done', 'cancel'])
    #         _logger.info(f"Pickings to cancel: {pickings_to_cancel}")
            
    #         for picking in pickings_to_cancel:
    #             _logger.info(f"examining picking: {picking.id} {picking.name} {picking.picking_type_id.id}")
    #             if picking.picking_type_id.id not in [6,7]:
    #                 _logger.info(f"not cancelling picking: {picking.id} {picking.name}")
    #                 continue
                
    #             for split_mo in split_mos:
    #                 split_mo.procurement_group_id = self.get_procurement_group(split_mo.name)
    #                 _logger.info(f"Creating new pickings for split MO: {split_mo.id} {split_mo.name}")
                    
    #                 if picking.picking_type_id.id == 6:
    #                     # Create a new picking for consumed materials (type 6)

    #                     pick_list_name = f"{split_mo.name}-[{split_mo.product_id.default_code}]"

    #                     pick_list_picking =  self.env['stock.picking'].create({
    #                         'name': pick_list_name,
    #                         'origin': split_mo.name,
    #                         'picking_type_id': 6,
    #                         'location_id': 8,
    #                         'location_dest_id': 17,
    #                         'group_id': self.get_procurement_group(split_mo.name),
    #                         'move_ids': [(0, 0, {
    #                             #'name': pick_list_name + str(move.id) + "-PL",
    #                             'name': pick_list_name,
    #                             'product_id': move.product_id.id,
    #                             'product_uom': move.product_uom.id,
    #                             'product_uom_qty': move.product_uom_qty,
    #                             'location_id': 8,
    #                             'location_dest_id': 17,
    #                             'origin': split_mo.name,
    #                             'reference': split_mo.name,
    #                             'bom_line_id' : move.bom_line_id.id,
    #                             'group_id': self.get_procurement_group(split_mo.name),
                                
    #                             #'raw_material_production_id': split_mo.id,
    #                             'picking_type_id': 6,
    #                             'bom_line_notes': move.bom_line_id.notes,
    #                         }) for move in split_mo.move_raw_ids]
    #                     })
    #                     # Update the location_dest_id of all the stock moves to 17
    #                     for move in pick_list_picking.move_ids:
    #                         move.location_dest_id = 17
    #                     pick_list_picking.action_confirm()
    #                     for move in pick_list_picking.move_ids:
    #                         move.location_dest_id = 17
    #                     # _logger.info(f"New pick list picking created and confirmed for split MO: {split_mo.id}")
                    
    #                 # elif picking.picking_type_id.id == 7:
    #                 #     # Create a new picking for finished products (type 7)
    #                 #     put_away_name = split_mo.name + "-PutAway"
    #                 #     put_away_picking = self.env['stock.picking'].create({
    #                 #         'name': put_away_name,
    #                 #         'origin': split_mo.name,
    #                 #         'picking_type_id': 7,  # Use the correct picking type ID for put away
    #                 #         'location_id': picking.location_id.id,
    #                 #         'location_dest_id': picking.location_dest_id.id,
    #                 #         'group_id': self.get_procurement_group(split_mo.name),
    #                 #         'move_ids': [(0, 0, {
    #                 #             'name': pick_list_name + str(move.id) + "-PA",
    #                 #             'product_id': move.product_id.id,
    #                 #             'product_uom': move.product_uom.id,
    #                 #             'product_uom_qty': split_mo.product_qty,  # Use the split MO's product quantity
    #                 #             'location_id': picking.location_id.id,
    #                 #             'location_dest_id': picking.location_dest_id.id,
    #                 #             'origin': split_mo.name,
    #                 #             'reference': split_mo.name,
    #                 #             'production_id': split_mo.id,
                                
    #                 #             # Remove the 'production_id' and 'raw_material_production_id' fields
    #                 #             'group_id': self.get_procurement_group(split_mo.name),
    #                 #             #'raw_material_production_id': split_mo.id,  # Keep the 'raw_material_production_id' field
    #                 #             'picking_type_id': 7,
    #                 #         }) for move in split_mo.move_finished_ids]  # Use split_mo.move_finished_ids
    #                 #     })
                        
    #                 #     put_away_picking.action_confirm()
    #                     # _logger.info(f"New put away picking created and confirmed for split MO: {split_mo.id}")
                
    #             picking.action_cancel()
        
    #     _logger.info("Exiting _split_productions function")
    #     return production_ids