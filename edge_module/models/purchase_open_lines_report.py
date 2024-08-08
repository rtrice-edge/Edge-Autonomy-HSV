from odoo import models, fields, api, tools

class PurchaseOpenLinesReport(models.Model):
    _name = 'purchase.open.lines.report'
    _description = 'Open Purchase Order Lines Report'
    _auto = False

    order_id = fields.Many2one('purchase.order', string='Purchase Order', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_qty = fields.Float(string='Quantity Ordered', readonly=True)
    price_unit = fields.Float(string='Unit Price', readonly=True)
    price_total = fields.Float(string='Total', readonly=True)
    amount_to_bill = fields.Float(string='Remaining to Bill', readonly=True)
    total_amount_to_bill = fields.Float(string='Total Remaining to Bill', compute='_compute_total_amount_to_bill')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE or REPLACE VIEW %s as (
                SELECT
                    pol.id as id,
                    po.id as order_id,
                    pol.product_id as product_id,
                    pol.product_qty as product_qty,
                    pol.price_unit as price_unit,
                    pol.price_total as price_total,
                    pol.price_total - pol.qty_invoiced * pol.price_unit as amount_to_bill
                FROM purchase_order_line pol
                JOIN purchase_order po ON (pol.order_id = po.id)
                WHERE po.state in ('purchase', 'done')
                AND pol.price_total > pol.qty_invoiced * pol.price_unit
            )
        """ % (self._table,))

    @api.depends('amount_to_bill')
    def _compute_total_amount_to_bill(self):
        total = sum(self.mapped('amount_to_bill'))
        for record in self:
            record.total_amount_to_bill = total