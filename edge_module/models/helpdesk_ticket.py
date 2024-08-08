from odoo import models, fields, api

class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')
    purchase_order_line_id = fields.Many2one('purchase.order.line', string='Purchase Order Line', domain="[('order_id', '=', purchase_order_id)]")
    subtype = fields.Selection([
        ('no_cofc', 'No CofC'),
        ('overshipped', 'Overshipped'),
        ('no_packing_slip', 'PO Arrived with no Packing Slip'),
        ('short_shipped', 'Short Shipped'),
        ('other', 'Other')
    ], string='Subtype')

    @api.onchange('purchase_order_id')
    def _onchange_purchase_order_id(self):
        self.purchase_order_line_id = False