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
            _logger.info(f"Stock Move Created: {mymove}")
            # log all the values in the stock move
            _logger.info(f"Stock Move Values: {vars(mymove)}")
            procurement_group_name = mymove.name
            if values.get('name') == '/':
                procurement_group_name = values['origin']
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