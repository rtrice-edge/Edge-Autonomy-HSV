from odoo import models, fields, api

class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')
    subtype = fields.Selection([
        ('no_cofc', 'No CofC'),
        ('overshipped', 'Overshipped'),
        ('no_packing_slip', 'PO Arrived with no Packing Slip'),
        ('short_shipped', 'Short Shipped'),
        ('other', 'Other')
    ], string='Subtype')