#odoo procurement category

from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime
import logging


_logger = logging.getLogger(__name__)

class StockMove(models.Model):
    _inherit = 'stock.move'
    receiptsmsl = fields.Selection(related='product_id.product_tmpl_id.msl', string='M.S.L', readonly=True, store=True)
    #maybe maybe maybe

    @api.model
    def create(self, values):
        _logger.info(values)
        if values.get('picking_type_id') and values['picking_type_id'] == 9:
            _logger.info('I am in the create method of stock.move and the picking type is 9!')
            # Generate a unique group_id based on current date and time
            group_id = self.env['stock.move']._generate_group_id(datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))
            values['group_id'] = group_id
        return super(StockMove, self).create(values)