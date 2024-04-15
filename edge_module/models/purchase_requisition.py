from odoo import api, models, fields

import logging
_logger = logging.getLogger(__name__)

class PurchaseRequisitionLine(models.Model):
    _inherit = "purchase.requisition.line"


    def _prepare_purchase_order_line(self, name, product_qty=0.0, price_unit=0.0, taxes_ids=False):
        _logger.info('Called _prepare_purchase_order_line')
        res = super(PurchaseRequisitionLine, self)._prepare_purchase_order_line(name, product_qty, price_unit, taxes_ids)
        _logger.info(self.product_description_variants + "product_description_variants" )
        _logger.info(name + "name")
        res['name'] = self.product_description_variants or name
        _logger.info(res['name'] + "res[name]")
        res['move_dest_ids'] = self.move_dest_id and [(4, self.move_dest_id.id)] or []
        return res