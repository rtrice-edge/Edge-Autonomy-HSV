from odoo import api, models, fields

import logging
_logger = logging.getLogger(__name__)


class PurchaseRequisitionLine(models.Model):
    _inherit = "purchase.requisition.line"



    def _prepare_purchase_order_line(self, name, product_qty=0.0, price_unit=0.0, taxes_ids=False):
        _logger.info('Called _prepare_purchase_order_line')
        name = self.product_description_variants or name
        _logger.info(f"Name before super(): {name}")
        res = super(PurchaseRequisitionLine, self)._prepare_purchase_order_line(name, product_qty, price_unit, taxes_ids)
        _logger.info(f"Name after super(): {res.get('name')}")
        return res