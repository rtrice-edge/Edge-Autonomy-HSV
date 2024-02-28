#odoo procurement category

from odoo import models, fields

class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'
    
    expensetype = fields.Selection([('officeSupplies','Office Supplies'),('meals', 'Meals')],string='Expense Type')