#odoo procurement category

from odoo import models, fields


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    expensetype = fields.Selection([('officeSupplies','Office Supplies'),('meals', 'Meals')],string='Expense Type')
