from odoo import api, models, fields

import logging
_logger = logging.getLogger(__name__)

class PurchaseRequisitionLine(models.Model):
    _inherit = "purchase.requisition.line"

    move_dest_id = fields.Many2one('stock.move', 'Downstream Move')

    def _prepare_purchase_order_line(self, name, product_qty=0.0, price_unit=0.0, taxes_ids=False):
        res = super(PurchaseRequisitionLine, self)._prepare_purchase_order_line(name, product_qty, price_unit, taxes_ids)
        res['name'] = self.product_description_variants or name
        res['move_dest_ids'] = self.move_dest_id and [(4, self.move_dest_id.id)] or []
        return res