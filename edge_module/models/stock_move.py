#odoo procurement category

from odoo import api, Command, fields, models
from odoo.osv import expression
from odoo.tools import float_compare, float_round, float_is_zero, OrderedSet
from datetime import datetime
import logging


_logger = logging.getLogger(__name__)

class StockMove(models.Model):
    _inherit = 'stock.move'
    receiptsmsl = fields.Selection(related='product_id.product_tmpl_id.msl', string='M.S.L', readonly=True, store=True)
    #maybe maybe maybe

    @api.model
    def create(self, values):
        _logger.info(f"Stock Move Create: {values}")
        if values.get('picking_type_id') and (values['picking_type_id'] == 9):
            # Generate a procurement_group based on the original receipt
            

            procurement_group_name = values.get('origin', False)
            _logger.info(f"Procurement Group Name: {procurement_group_name}")
            procurement_group = self.env['procurement.group'].search([('name', '=', procurement_group_name)])
            if not procurement_group:
                _logger.info("Procurement Group not found, creating new one...")
                procurement_group = self.env['procurement.group'].create({'name': procurement_group_name})
                _logger.info(f"New Procurement Group created: {procurement_group}")
            else:
                _logger.info(f"Procurement Group already exists: {procurement_group}")
            values['group_id'] = procurement_group.id
            _logger.info(f"Procurement Group ID assigned: {procurement_group.id}")
        elif values.get('picking_type_id') and (values['picking_type_id'] in [6,7,8]):
            # I call the real Create method and then adjust the values after.  
            mymove = super(StockMove, self).create(values)
            
            procurement_group_name = mymove.name
            _logger.info(f"Procurement Group Name: {procurement_group_name}")
            procurement_group = self.env['procurement.group'].search([('name', '=', procurement_group_name)])
            if not procurement_group:
                _logger.info("Procurement Group not found, creating new one...")
                procurement_group = self.env['procurement.group'].create({'name': procurement_group_name})
                _logger.info(f"New Procurement Group created: {procurement_group}")
            else:
                _logger.info(f"Procurement Group already exists: {procurement_group}")
                
            mymove.group_id = procurement_group.id
            return mymove

             
        return super(StockMove, self).create(values)
    
    def action_explode(self):
        """ Explodes pickings """
        # in order to explode a move, we must have a picking_type_id on that move because otherwise the move
        # won't be assigned to a picking and it would be weird to explode a move into several if they aren't
        # all grouped in the same picking.
        _logger.info(f"Action Explode: {self}")
        moves_ids_to_return = OrderedSet()
        moves_ids_to_unlink = OrderedSet()
        phantom_moves_vals_list = []
        for move in self:
            _logger.info(f"Move: {move}")
            _logger.info(f"Move Picking Type ID: {move.picking_type_id}")
            _logger.info(f"Move Production ID: {move.production_id}")   
            _logger.info(f"Move context is_scrap: {self.env.context.get('is_scrap')}")
            if (not move.picking_type_id and not self.env.context.get('is_scrap')) or (move.production_id and move.production_id.product_id == move.product_id):
                _logger.info(f"Move not assigned to a picking or is a production move, skipping")
                moves_ids_to_return.add(move.id)
                continue
            bom = self.env['mrp.bom'].sudo()._bom_find(move.product_id, company_id=move.company_id.id, bom_type='phantom')[move.product_id]
            _logger.info(f"BOM: {bom}")
            if not bom:
                _logger.info(f"No BOM found for product {move.product_id}, skipping")
                moves_ids_to_return.add(move.id)
                continue
            if float_is_zero(move.product_uom_qty, precision_rounding=move.product_uom.rounding):
                factor = move.product_uom._compute_quantity(move.quantity, bom.product_uom_id) / bom.product_qty
            else:
                factor = move.product_uom._compute_quantity(move.product_uom_qty, bom.product_uom_id) / bom.product_qty
            boms, lines = bom.sudo().explode(move.product_id, factor, picking_type=bom.picking_type_id)
            for bom_line, line_data in lines:
                _logger.info(f"BOM Line: {bom_line}")
                if float_is_zero(move.product_uom_qty, precision_rounding=move.product_uom.rounding) or self.env.context.get('is_scrap'):
                    phantom_moves_vals_list += move._generate_move_phantom(bom_line, 0, line_data['qty'])
                else:
                    phantom_moves_vals_list += move._generate_move_phantom(bom_line, line_data['qty'], 0)
            # delete the move with original product which is not relevant anymore
            _logger.info(f"Adding move to unlink: {move}")
            moves_ids_to_unlink.add(move.id)

        if phantom_moves_vals_list:
            _logger.info(f"Creating phantom moves: {phantom_moves_vals_list}")
            phantom_moves = self.env['stock.move'].create(phantom_moves_vals_list)
            phantom_moves._adjust_procure_method()
            moves_ids_to_return |= phantom_moves.action_explode().ids
        move_to_unlink = self.env['stock.move'].browse(moves_ids_to_unlink).sudo()
        move_to_unlink.quantity = 0
        move_to_unlink._action_cancel()
        move_to_unlink.unlink()
        _logger.info(f"Returning moves: {moves_ids_to_return}")
        return self.env['stock.move'].browse(moves_ids_to_return)