from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class PurchaseRequestApprover(models.Model):
    _name = 'purchase.request.approver'
    _description = 'Purchase Request Approver'
    _rec_name = 'user_id'

    user_id = fields.Many2one('res.users', string='User', required=True)
    company_id = fields.Many2one('res.company', string='Company', 
                                default=lambda self: self.env.company)
    manager_level = fields.Selection([
        ('dept_mgr', 'Department Manager'),
        ('prog_mgr', 'Program Manager'),
        ('sc_mgr', 'Supply Chain Manager'),
        ('gm_coo', 'GM/COO'),
        ('exec', 'Executive'),
    ], string='Manager Level', required=True, default='dept_mgr')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_user_manager_level', 'unique(user_id, manager_level)', 
         'This user is already an approver for that manager level!')
    ]

    def name_get(self):
        return [(record.id, record.user_id.name) for record in self]