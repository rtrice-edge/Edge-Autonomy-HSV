#odoo procurement category

from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    procurementcategory = fields.Selection([('officeSupplies','Office Supplies'),('meals', 'Meals')],string='Procurement Category')