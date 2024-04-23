from odoo import models, api, fields

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    tracking_number = fields.Char(string='Tracking Number')
    carrier = fields.Char(string='Carrier')
    currency_deliveries = fields.Curency(string="Currency")
    shipping_price = fields.Monetary(string='Shipping Price', default=0.0)