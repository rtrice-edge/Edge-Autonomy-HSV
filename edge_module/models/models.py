#odoo procurement category

from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    procurementcategory = fields.Selection([('Office Supplies'),('Meals')],string='Procurement Category', required=True)