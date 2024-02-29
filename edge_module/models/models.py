#odoo procurement category

from odoo import models, fields


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    expensetype = fields.Selection([
        ('direct', 'Direct'),
        ('g&a', 'G & A'),
        ('ir&d', 'IR & D')
    ], string='Expense Type', required=True)

    expensetype = fields.Selection(
        selection='_get_selection_2', string='Expense Type')

    @staticmethod
    def _get_selection_2():
        SELECTION_LIST_2 = [('officesupplies', 'Office Supplies'), ('meal', 'Meals')]
        SELECTION_LIST_3 = [('expense1', 'Expense 1'), ('expense2', 'Expense 2')]

        return SELECTION_LIST_2 + SELECTION_LIST_3