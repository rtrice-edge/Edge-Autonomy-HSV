from odoo import models, api, fields

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    tracking_number = fields.Char(string='Tracking Number')
    carrier = fields.Char(string='Carrier')
    currency_id = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True)
    delivery_price = fields.Monetary('Delivery Cost', currency_field='currency_id', default=0.0)