#odoo procurement category

from odoo import models, fields


class PurchaseOrder(models.Model):
    _name = 'purchase.order'

    expensetype = fields.Selection([
        ('direct', 'Direct'),
        ('g&a', 'G & A'),
        ('ir&d', 'IR&D')
    ], string='Expense Type', required=True)

    expensetype2 = fields.Selection(
        selection='_get_selection_2', string='Expense Type')

    def _get_selection_2(self):
        # Define SELECTION_LIST_2 and SELECTION_LIST_3 somewhere in your code
        SELECTION_LIST_2 = [('officesupplies', 'Office Supplies'), ('meal', 'Meals')]
        SELECTION_LIST_3 = [('officesupplies', 'Office Supplies'), ('meal', 'Meals')]
        
        selected = self.expensetype
        if selected == 'direct':
            return SELECTION_LIST_2
        else:
            return SELECTION_LIST_3
