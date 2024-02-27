#odoo visual studio

from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    anewfield = fields.Boolean('A New Field', required=True)