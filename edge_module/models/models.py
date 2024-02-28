#odoo visual studio

from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    procurementcategory = fields.Boolean('Procurement Category', required=True)