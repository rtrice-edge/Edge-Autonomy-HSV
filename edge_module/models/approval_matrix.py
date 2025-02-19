from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ApprovalMatrix(models.Model):
    _name = 'approval.matrix'
    _description = 'Purchase Approval Matrix'
    _rec_name = 'job_id'


    job_id = fields.Many2one('job', string='Job', required=False)
    job_text = fields.Char(string='Job Text', required=False)
    job_comparison = fields.Selection(
        selection=[('is', 'Is'), ('contains', 'Contains')],
        string='Job Comparison',
        required=True,
        default='is',
        help='Select "Is" to match a job exactly, or "Contains" to match any job containing the text specified'
    )

    expense_type = fields.Selection(
        selection='_get_expense_type_selection',
        string='Expense Type',
        required=False
    )

    min_amount = fields.Float(string='Minimum Amount', required=True)
    max_amount = fields.Float(string='Maximum Amount', required=True)
    
    # Using the manager_level selection via a related field's selection attribute
    first_approver_level = fields.Selection(
        selection='_get_manager_level_selection',
        string='First Approver Level', 
        required=True
    )
    
    second_approver_level = fields.Selection(
        selection='_get_manager_level_selection',
        string='Second Approver Level'
    )
    
    third_approver_level = fields.Selection(
        selection='_get_manager_level_selection',
        string='Third Approver Level'
    )

    @api.depends('job_comparison')
    def _reset_job_fields(self):
        for record in self:
            if record.job_comparison == 'is':
                record.job_text = False
            else:
                record.job_id = False


    @api.model
    def _get_expense_type_selection(self):
        return self.env['purchase.order.line']._fields['expense_type'].selection

    @api.model
    def _get_manager_level_selection(self):
        return self.env['purchase.request.approver']._fields['manager_level'].selection

    _sql_constraints = [
        ('unique_job_range', 
         'UNIQUE(job_id, min_amount, max_amount)',
         'An approval matrix entry already exists for this job and amount range!')
    ]

    @api.constrains('min_amount', 'max_amount')
    def _check_amount_range(self):
        for record in self:
            if record.min_amount >= record.max_amount:
                raise ValidationError(_('Maximum amount must be greater than minimum amount'))

    @api.constrains('first_approver_level', 'second_approver_level', 'third_approver_level')
    def _check_approver_levels(self):
        for record in self:
            levels = [level for level in [record.first_approver_level, 
                                        record.second_approver_level, 
                                        record.third_approver_level] if level]
            if len(levels) != len(set(levels)):
                raise ValidationError(_('Approver levels must be different'))