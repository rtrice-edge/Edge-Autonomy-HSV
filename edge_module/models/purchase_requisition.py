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
    
    def _compute_ordered_qty(self):
        line_found = set()
        for line in self:
            total = 0.0
            for po in line.requisition_id.purchase_ids.filtered(lambda purchase_order: purchase_order.state in ['purchase', 'done']):
                #for po_line in po.order_line.filtered(lambda order_line: order_line.product_id == line.product_id and order_line.name == line.product_description_variants):
                for po_line in po.order_line.filtered(lambda order_line: order_line.name == line.product_description_variants):
                    if po_line.product_uom != line.product_uom_id:
                        total += po_line.product_uom._compute_quantity(po_line.product_qty, line.product_uom_id)
                    else:
                        total += po_line.product_qty
            if (line.product_id, line.product_description_variants) not in line_found:
                line.qty_ordered = total
                line_found.add((line.product_id, line.product_description_variants))
            else:
                line.qty_ordered = 0