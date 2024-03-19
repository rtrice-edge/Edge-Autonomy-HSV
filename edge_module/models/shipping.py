from odoo import models, api, fields

class Shipping(models.Model):
    _inherit = 'stock.picking'

    tracking_number = fields.Text(string='Tracking Number')