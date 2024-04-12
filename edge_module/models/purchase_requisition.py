from odoo import api, models, _logger

class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    def action_create_purchase_order(self):
        _logger.info('Called action_create_purchase_order')
        res = super(PurchaseRequisition, self).action_create_purchase_order()
        for requisition in self:
            _logger.info('Processing requisition: %s', requisition.name)
            for po in requisition.purchase_ids:
                _logger.info('Processing purchase order: %s', po.name)
                for line in requisition.line_ids:
                    _logger.info('Processing requisition line: %s', line.product_id.name)
                    po_line = po.order_line.filtered(lambda l: l.product_id == line.product_id)
                    if po_line:
                        _logger.info('Updating purchase order line description')
                        po_line.name = line.product_description_variants
        return res