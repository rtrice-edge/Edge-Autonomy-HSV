from odoo import models, fields, api, tools

class PurchaseOpenLinesReport(models.Model):
    _name = 'purchase.open.lines.report'
    _description = 'Open Purchase Order Lines Report'
    _auto = False

    order_id = fields.Many2one('purchase.order', string='Purchase Order', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_qty = fields.Float(string='Quantity to Receive', readonly=True)
    price_unit = fields.Float(string='Unit Price', readonly=True)
    price_subtotal = fields.Float(string='Subtotal', readonly=True, compute='_compute_price_subtotal', store=True)
    total_amount = fields.Float(string='Total Amount', compute='_compute_total_amount')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE or REPLACE VIEW %s as (
                SELECT
                    pol.id as id,
                    po.id as order_id,
                    pol.product_id as product_id,
                    pol.product_qty - pol.qty_received as product_qty,
                    pol.price_unit as price_unit
                FROM purchase_order_line pol
                JOIN purchase_order po ON (pol.order_id = po.id)
                WHERE po.state in ('purchase', 'done')
                AND pol.product_qty > pol.qty_received
            )
        """ % (self._table,))

    @api.depends('product_qty', 'price_unit')
    def _compute_price_subtotal(self):
        for record in self:
            record.price_subtotal = record.product_qty * record.price_unit

    @api.depends('price_subtotal')
    def _compute_total_amount(self):
        total = sum(self.mapped('price_subtotal'))
        for record in self:
            record.total_amount = total