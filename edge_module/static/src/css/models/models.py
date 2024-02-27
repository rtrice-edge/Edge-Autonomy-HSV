#odoo visual studio

from odoo import models, fields

class ProductVariant(models.Model):
    _inherit = 'product.product'
    
    anewfield = fields.Boolean('A New Field', required=True)