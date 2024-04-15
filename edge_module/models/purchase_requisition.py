from odoo import api, models, fields

import logging
_logger = logging.getLogger(__name__)

class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    def button_confirm(self):
        _logger.info('Called button_confirm')
        res = super(PurchaseRequisition, self).button_confirm()
        for requisition in self:
            for po in requisition.purchase_ids:
                for line in po.order_line:
                    if line.requisition_line_id:
                        _logger.info('Updating product description from PR line')
                        line.name = line.requisition_line_id.product_description_variants or line.name
        return res

class PurchaseRequisitionLine(models.Model):
    _inherit = "purchase.requisition.line"


    def _prepare_purchase_order_line(self, name, product_qty=0.0, price_unit=0.0, taxes_ids=False):
        res = super(PurchaseRequisitionLine, self)._prepare_purchase_order_line(name, product_qty, price_unit, taxes_ids)
        res['name'] = self.product_description_variants or name
        _logger.info(res['name'] + "res[name]")
        res['move_dest_ids'] = self.move_dest_id and [(4, self.move_dest_id.id)] or []
        return res