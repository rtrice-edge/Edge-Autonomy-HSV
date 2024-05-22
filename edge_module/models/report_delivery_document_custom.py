from odoo import models, fields

class StockPickingInherit(models.Model):
    _inherit = 'stock.picking'

    delivery_edge_recipient = fields.Char(compute='_compute_edge_recipient', string='Edge Recipient')

    def _compute_edge_recipient(self):
        for picking in self:
            purchase_order = self.env['purchase.order'].search([('picking_ids', 'in', picking.id)], limit=1)
            if purchase_order:
                picking.delivery_edge_recipient = purchase_order.edge_recipient
            else:
                picking.delivery_edge_recipient = False