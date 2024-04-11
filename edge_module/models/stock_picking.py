from odoo import models, api, fields

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    tracking_number = fields.Char(string='Tracking Number')