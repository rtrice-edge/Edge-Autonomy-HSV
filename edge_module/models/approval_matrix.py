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
    
    # Changed field names to use numeric suffixes
    approver_level_1 = fields.Selection(
        selection='_get_manager_level_selection',
        string='Approval Level 1', 
        required=True
    )
    
    approver_level_2 = fields.Selection(
        selection='_get_manager_level_selection',
        string='Approval Level 2'
    )
    
    approver_level_3 = fields.Selection(
        selection='_get_manager_level_selection',
        string='Approval Level 3'
    )

    approver_level_4 = fields.Selection(
        selection='_get_manager_level_selection',
        string='Approval Level 4'
    )

    approver_level_5 = fields.Selection(
        selection='_get_manager_level_selection',
        string='Approval Level 5'
    )

    approver_level_6 = fields.Selection(
        selection='_get_manager_level_selection',
        string='Approval Level 6'
    )

    approver_level_7 = fields.Selection(
        selection='_get_manager_level_selection',
        string='Approval Level 7'
    )

    approver_level_8 = fields.Selection(
        selection='_get_manager_level_selection',
        string='Approval Level 8'
    )

    approver_level_9 = fields.Selection(
        selection='_get_manager_level_selection',
        string='Approval Level 9'
    )

    approver_level_10 = fields.Selection(
        selection='_get_manager_level_selection',
        string='Approval Level 10'
    )

    approver_level_11 = fields.Selection(
        selection='_get_manager_level_selection',
        string='Approval Level 11'
    )

    approver_level_12 = fields.Selection(
        selection='_get_manager_level_selection',
        string='Approval Level 12'
    )

    approver_level_13 = fields.Selection(
        selection='_get_manager_level_selection',
        string='Approval Level 13'
    )

    approver_level_14 = fields.Selection(
        selection='_get_manager_level_selection',
        string='Approval Level 14'
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

    @api.constrains('approver_level_1', 'approver_level_2', 'approver_level_3', 'approver_level_4',
                    'approver_level_5', 'approver_level_6', 'approver_level_7', 'approver_level_8',
                    'approver_level_9', 'approver_level_10', 'approver_level_11', 'approver_level_12'
                    'approver_level_13', 'approver_level_14')
    def _check_approver_levels(self):
        for record in self:
            # First check that levels are different (existing constraint)
            levels = [getattr(record, f'approver_level_{i}') for i in range(1, 15) if getattr(record, f'approver_level_{i}', False)]
            if len(levels) != len(set(levels)):
                raise ValidationError(_('Approver levels must be different'))
            
            # Then check that if a level is set, all previous levels are also set
            for i in range(2, 15):
                current_level = getattr(record, f'approver_level_{i}')
                if current_level:  # If this level is set
                    prev_level = getattr(record, f'approver_level_{i-1}')
                    if not prev_level:
                        raise ValidationError(_(
                            f'You cannot set approval level {i} without setting level {i-1}. '
                            f'All levels before {i} must be set.'
                        ))
