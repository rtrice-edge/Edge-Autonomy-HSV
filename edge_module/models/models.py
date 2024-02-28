#odoo visual studio

from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    procurementcategory = fields.Selection('Procurement Category', required=True)