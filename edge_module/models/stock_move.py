#odoo procurement category

from odoo import api, Command, fields, models
from odoo.osv import expression
from odoo.tools import float_compare, float_round, float_is_zero, OrderedSet
from datetime import datetime
import logging
import math


_logger = logging.getLogger(__name__)

class StockMove(models.Model):
    _inherit = 'stock.move'
    receiptsmsl = fields.Selection(related='product_id.product_tmpl_id.msl', string='M.S.L', readonly=True, store=True)
    #maybe maybe maybe

    @api.model
    def create(self, values):
        
        if values.get('picking_type_id') and (values['picking_type_id'] == 9):
            # Generate a procurement_group based on the original receipt
            

            procurement_group_name = values.get('origin', False)
           
            procurement_group = self.env['procurement.group'].search([('name', '=', procurement_group_name)])
            if not procurement_group:
                _logger.info("Procurement Group not found, creating new one...")
                procurement_group = self.env['procurement.group'].create({'name': procurement_group_name})
                _logger.info(f"New Procurement Group created: {procurement_group}")
            values['group_id'] = procurement_group.id

            
            
        elif values.get('picking_type_id') and (values['picking_type_id'] in [6,7]):
                        # I call the real Create method and then adjust the values after.  

            mymove = super(StockMove, self).create(values)
            _logger.info(f"Stock Move Created: {mymove}")
            # log all the values in the stock move
            _logger.info(f"Stock Move Values: {mymove.name} {mymove.origin} {mymove.group_id} {mymove.picking_type_id} {mymove.product_id} {mymove.product_uom_qty} {mymove.product_uom} {mymove.location_id} {mymove.location_dest_id} ")
            procurement_group_name = values['origin']
            procurement_group = self.env['procurement.group'].search([('name', '=', procurement_group_name)])
            if not procurement_group:
                _logger.info("Procurement Group not found, creating new one...")
                procurement_group = self.env['procurement.group'].create({'name': procurement_group_name})
                _logger.info(f"New Procurement Group created: {procurement_group}")
            # The following code sets both the group id to keep things separate, and the location and destination to the correct values
            mymove.group_id = procurement_group.id
            if (mymove.picking_type_id.id == 6):
                mymove.location_dest_id = 15
            if (mymove.picking_type_id.id == 7):
                mymove.location_id = 18
            _logger.info("My location and destinations are" + str(mymove.location_id) + " " + str(mymove.location_dest_id))
            return mymove

             
        return super(StockMove, self).create(values)
    
    def _compute_quantity(self):
        """
        This field represents the sum of the move lines `quantity`. It allows the user to know
        if there is still work to do.

        We take care of rounding this value to the nearest whole number using the `ceil` function
        to ensure that the quantity is always rounded up.
        """
        super()._compute_quantity()

        for move in self:
            move.quantity = math.ceil(move.quantity)
            
    def _prepare_mo_qty(self, quantity):
        res = super(StockMove, self)._prepare_mo_qty(quantity)
        _logger.info(f"I called prepare_mo_qty: {res}")
        _logger.info(f"self.picking_type_id.id: {self.picking_type_id.id}")
        if (self.picking_type_id.id == 6):
            res['location_id'] = self.location_id.id  # Use the specified location_id instead of the production location
        return res