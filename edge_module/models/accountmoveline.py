from odoo import models, fields

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    job_number = fields.Char(related='purchase_line_id.job_number', store=False, string="Job Number", readonly=True)
    expense_type = fields.Selection(related='purchase_line_id.expense_type', store=False, string="Expense Type", readonly=True)
