#odoo procurement category

from odoo import models, fields


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    expensetype = fields.Selection([
        ('direct', 'Direct'),
        ('g&a', 'G & A'),
        ('ir&d', 'IR&D')
    ], string='Expense Type', required=True)

    expensetype2 = fields.Selection(
        selection='_get_selection_2', string='Expense Type')

    @staticmethod
    def _get_selection_2():
        SELECTION_LIST_2 = [
            ('direct', [
                ('officesupplies', 'Office Supplies'),
                ('meal', 'Meals')
            ]),
            ('g&a', [
                ('officesupplies', 'Office Supplies'),
                ('meal', 'Meals')
            ]),
            ('ir&d', [
                ('officesupplies', 'Office Supplies'),
                ('meal', 'Meals')
            ])
        ]
        return SELECTION_LIST_2