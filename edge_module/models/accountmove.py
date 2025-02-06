from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    jamis_bill_ids = fields.One2many('jamis.bills', 'move_id', string='Jamis Bills')

    def action_add_bill_to_jamis(self):
        # This method will be called when the button is clicked
        # For now, we'll just pass and implement the logic later
        pass
    def _recompute_dynamic_lines(self, recompute_all_taxes=False, recompute_tax_base_amount=False):
        res = super(AccountMove, self)._recompute_dynamic_lines(recompute_all_taxes, recompute_tax_base_amount)
        
        for move in self:
            for line in move.invoice_line_ids:
                if line.purchase_line_id:
                    line.job_number = line.purchase_line_id.job_number
                    line.expense_type = line.purchase_line_id.expense_type
        
        return res