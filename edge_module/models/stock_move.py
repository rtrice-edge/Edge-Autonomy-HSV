#odoo procurement category

from odoo import models, fields, api

class StockMove(models.Model):
    _inherit = 'stock.move'
    receiptsmsl = fields.Selection(related='product_id.product_tmpl_id.msl', string='M.S.L', readonly=True, store=True)
    #maybe maybe maybe

    @api.model
    def create(self, values):
        if values.get('operation_type') == 'receiving_inspection':
            values['merge_transfer'] = False
        return super(StockMove, self).create(values)