#odoo procurement category

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class StockMove(models.Model):
    _inherit = 'stock.move'
    receiptsmsl = fields.Selection(related='product_id.product_tmpl_id.msl', string='M.S.L', readonly=True, store=True)
    #maybe maybe maybe

    @api.model
    def create(self, values):
        _logger.info(f"Stock Move create: {values}")
        if values.get('operation_type') == 'receiving_inspection':
            values['merge_transfer'] = False
        return super(StockMove, self).create(values)