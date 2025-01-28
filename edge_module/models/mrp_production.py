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





#when a manufacturing order is confirmed, split the pick list into multiple pick lists based on the source location of the move lines

class MrpProduction(models.Model):
    _inherit = 'mrp.production'
    alias = fields.Char(string='Alias', compute='_compute_alias', store=False,
                        help='Helps to identify the MO in the system')

    is_post_edit_allowed = fields.Boolean(
        compute='_compute_post_edit_allowed'
    )
    ### This logic will undo a cancel
    ### It will set the state of the MO to 'progress'
    def action_undo_cancel(self):
        for production in self:
            if production.state != 'cancel':
                raise UserError("Only canceled MOs can be undone.")

            # Reset MO state
            production.state = 'progress'
            production.date_finished = False
            # Restore stock moves
            self._restore_stock_moves()

            # Restore work orders
            self._restore_work_orders()

    def button_mark_done(self):
        """
        Overrides the Produce All button behavior to add reverse moves
        for RMA location for 'RMA Work' MOs.
        """
        mo = super(MrpProduction, self).button_mark_done()
        
        # Check if the MO type is "RMA Work"
        if self.picking_type_id.id == 13:
            _logger.info(f"Creating reverse moves for RMA MO: {self.id}")
            Location = self.env['stock.location']
            rma_wip = Location.search([('complete_name', '=', 'HSV/RMA WIP')], limit=1)
            
            # Find the finished moves
            for original_move in self.move_finished_ids:
                if original_move.location_dest_id == rma_wip:
                    # Create reverse move with same origin
                    reverse_move = original_move.copy({
                        'location_id': original_move.location_dest_id.id,  # Swap source
                        'location_dest_id': original_move.location_id.id,  # Swap destination
                        'product_uom_qty': original_move.product_uom_qty,
                        'quantity_done': original_move.quantity_done,
                        'production_id': self.id,
                        # Keep the same origin to group the moves together
                    })
                    # Immediately mark the reverse move as done
                    reverse_move._action_done()

        return mo
    def _restore_stock_moves(self):
        for move in self.move_raw_ids + self.move_finished_ids:
            if move.state == 'cancel':
                # Un-cancel the stock move
                move.state = 'confirmed'
                
                # Create corresponding stock move lines
                for move_line_data in self._prepare_move_line_data(move):
                    self.env['stock.move.line'].create(move_line_data)

    def _prepare_move_line_data(self, move):
        """
        Prepare data for creating stock.move.line records based on the stock.move.
        """
        move_line_data = {
            'move_id': move.id,
            'product_id': move.product_id.id,
            'product_uom_id': move.product_uom.id,
            'location_id': move.location_id.id,
            'location_dest_id': move.location_dest_id.id,
            'qty_done': 0,  # Initially, no quantity is done
            'lot_id': None,  # Add logic for lots/serials if needed
        }
        return [move_line_data]

    def _restore_work_orders(self):
        """
        Restore canceled work orders for the MO. Set the first canceled work order
        to 'ready' and others to 'waiting'.
        """
        canceled_work_orders = self.workorder_ids.filtered(lambda wo: wo.state == 'cancel')

        # Sort by 'sequence_number'
        sorted_work_orders = canceled_work_orders.sorted('sequence_number')

        for index, workorder in enumerate(sorted_work_orders):
            if index == 0:
                workorder.state = 'ready'
                if workorder.date_finished:
                    workorder.date_finished = False
            else:
                workorder.state = 'waiting'
                if workorder.date_start:
                    workorder.date_start = False

                # Clear finish times for canceled work orders
                if workorder.date_finished:
                    workorder.date_finished = False


                
    ######        
                
                

    def action_open_additional_consumption_wizard(self):
        self.ensure_one()
        action = {
            'name': 'Add Additional Consumption',
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.additional.consumption.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_production_id': self.id,
                'default_location_src_id': self.location_src_id.id,
            }
        }
        return action
    
    def _compute_post_edit_allowed(self):
        can_edit = self.env.user.has_group('edge_module.group_mo_post_edit')
        for record in self:
            record.is_post_edit_allowed = can_edit
            
    def write(self, vals):
        if self.state == 'done' and not self.env.user.has_group('edge_module.group_mo_post_edit'):
            raise UserError(_("Only authorized users can modify completed MOs"))
        return super().write(vals)
            
    
    def action_scrap_all_and_cancel(self):
        self.ensure_one()
        if self.state in ['done', 'cancel']:
            raise UserError(_("Cannot scrap products for completed or cancelled manufacturing orders."))
            
        moves_to_scrap = self.move_raw_ids.filtered(
            lambda m: m.product_id.type == 'product' and 
                     m.state not in ('done', 'cancel') and
                     m.product_id.tracking in ('lot', 'serial')
        )
        
        Scrap = self.env['stock.scrap']
        for move in moves_to_scrap:
            picked_lines = move.move_line_ids.filtered(lambda l: l.picked and l.lot_id)
            for move_line in picked_lines:
                scrap_vals = {
                    'production_id': self.id,
                    'product_id': move.product_id.id,
                    'product_uom_id': move.product_uom.id,
                    'scrap_qty': move_line.quantity,
                    'location_id': move_line.location_id.id,
                    'lot_id': move_line.lot_id.id,
                }
                scrap = Scrap.create(scrap_vals)
                scrap.action_validate()
            
        self.action_cancel()
        
        return {'type': 'ir.actions.act_window_close'}
    
    
      
    @api.model
    def create(self, vals):
        # First create the MO using the standard method
        mo = super(MrpProduction, self).create(vals)
        
        # Get the product's category
        product = mo.product_id
        category = product.categ_id
        
        # Define location references
        Location = self.env['stock.location']
        hsv_cage = Location.search([('complete_name', '=', 'HSV/Cage')], limit=1)
        hsv_kit_shelves = Location.search([('complete_name', '=', 'HSV/Cage/Kit Shelves')], limit=1)
        hsv_wip = Location.search([('complete_name', '=', 'HSV/WIP')], limit=1)
        rma_wip = Location.search([('complete_name', '=', 'HSV/RMA WIP')], limit=1)
        #if picking type id is 13 then we should skip over the rest of this.
        _logger.info(f"Category: {category.name}")
        _logger.info(f"Picking Type: {mo.picking_type_id.id}")
        if mo.picking_type_id.id == 13:
            mo.location_src_id = rma_wip.id
            mo.location_dest_id = rma_wip.id
            
                # if the BOM ID isn't set... assume its an RMA
        elif category.name == 'Manufactured Wire':
            mo.location_src_id = hsv_cage.id
            # Get the putaway rule for this product
            PutawayRule = self.env['stock.putaway.rule']
            putaway_location = PutawayRule.search([
                ('product_id', '=', product.id),
                ('location_in_id', '=', hsv_cage.id),
            ], limit=1)
            
            # If no product-specific rule, try category-based rule
            if not putaway_location:
                putaway_location = PutawayRule.search([
                    ('category_id', '=', category.id),
                    ('location_in_id', '=', hsv_cage.id),
                ], limit=1)
            
            # Use the putaway location if found, otherwise fallback to cage
            mo.location_dest_id = putaway_location.location_out_id.id if putaway_location else hsv_cage.id
            
        elif category.name == 'Kit':
            mo.location_src_id = hsv_cage.id
            mo.location_dest_id = hsv_kit_shelves.id
        else:
            mo.location_src_id = hsv_wip.id
            mo.location_dest_id = hsv_cage.id
            
        return mo

    def write(self, vals):
        result = super(MrpProduction, self).write(vals)
        
        # If product has changed, update locations
        if 'product_id' in vals:
            for mo in self:
                mo = super(MrpProduction, self).create(vals)
        
                # Get the product's category
                product = mo.product_id
                sq = self.env['stock.quant'].search([
                    ('product_id', '=', product.id)
                ], order='quantity desc', limit=1)


                category = product.categ_id
                
                Location = self.env['stock.location']
                hsv_cage = Location.search([('complete_name', '=', 'HSV/Cage')], limit=1)
                hsv_kit_shelves = Location.search([('complete_name', '=', 'HSV/Cage/Kit Shelves')], limit=1)
                hsv_wip = Location.search([('complete_name', '=', 'HSV/WIP')], limit=1)
                rma_wip = Location.search([('complete_name', '=', 'HSV/RMA WIP')], limit=1)
                _logger.info(f"Category: {category.name}")
                _logger.info(f"Picking Type: {mo.picking_type_id.id}")
                if mo.picking_type_id.id == 13:
                    mo.location_src_id = rma_wip.id
                    mo.location_dest_id = rma_wip.id
                
                
                elif category.name == 'Manufactured Wire':
                    mo.location_src_id = hsv_cage.id
                    mo.location_dest_id = sq.location_id.id
                elif category.name == 'Kit':
                    mo.location_src_id = hsv_cage.id
                    mo.location_dest_id = hsv_kit_shelves.id
                else:
                    mo.location_src_id = hsv_wip.id
                    mo.location_dest_id = hsv_cage.id
                    
        return result
    
    
    
    def get_initials(self, name):
        return ''.join([word[0].upper() for word in name.split() if word])

    def get_worker_times(self):
        worker_times = {}
        for workorder in self.workorder_ids:
            for time_log in workorder.time_ids:
                worker = time_log.user_id
                if worker not in worker_times:
                    worker_times[worker] = {'initials': self.get_initials(worker.name), 'time': 0}
                worker_times[worker]['time'] += time_log.duration
        return worker_times
  

    def reset_operation(self):
        for production in self:
            current_operation = production.workorder_ids.filtered(lambda w: w.state == 'progress')
            if current_operation:
                current_operation.write({'state': 'pending'})
                previous_operation = production.workorder_ids.filtered(lambda w: w.next_work_order_id == current_operation)
                if previous_operation:
                    previous_operation.write({'state': 'ready'})
                    


    
    @api.depends('name', 'product_id.default_code')
    def _compute_alias(self):
        for production in self:
            if production.name and production.product_id.default_code:
                production.alias = f"{production.name}-[{production.product_id.default_code}]"
            else:
                production.alias = False


    def action_change_locations(self):
        view_id = self.env.ref('your_module.view_manufacturing_order_location_change_form').id
        return {
            'name': 'Change Manufacturing Order Locations',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mrp.production.location.change',
            'views': [(view_id, 'form')],
            'target': 'new',
            'context': {
                'default_mo_id': self.id,
                'default_location_src_id': self.location_src_id.id,
                'default_location_dest_id': self.location_dest_id.id,
            }
        }
            

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