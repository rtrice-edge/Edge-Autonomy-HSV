from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class PurchaseRequestApprover(models.Model):
    _name = 'purchase.request.approver'
    _description = 'Purchase Request Approver'
    _rec_name = 'user_id'
    _order = 'manager_level_rank desc, superior_level_rank desc'

    user_id = fields.Many2one('res.users', string='User', required=True)
    company_id = fields.Many2one('res.company', string='Company', 
                                default=lambda self: self.env.company)
    manager_level = fields.Selection([
        ('dept_supv', 'Department Supervisor'),
        ('dept_mgr', 'Department Manager'),
        ('prog_mgr', 'Program Manager'),
        ('safety_mgr', 'Safety Manager'),
        ('it_mgr', 'IT Manager'),
        ('sc_mgr', 'Supply Chain Manager'),
        ('dept_dir' ,'Department Director'),
        ('gm_coo', 'Site GM'),
        ('cto', 'CTO'),
        ('cgo', 'CGO'),
        ('coo', 'COO'),
        ('cpo', 'CPO'),
        ('cfo', 'CFO'),
        ('ceo', 'CEO')
    ], string='Manager Level', required=True, default='dept_supv')

    superior_level = fields.Selection([
        ('dept_mgr', 'Department Manager'),
        ('prog_mgr', 'Program Manager'),
        ('safety_mgr', 'Safety Manager'),
        ('it_mgr', 'IT Manager'),
        ('sc_mgr', 'Supply Chain Manager'),
        ('dept_dir' ,'Department Director'),
        ('gm_coo', 'Site GM'),
        ('cto', 'CTO'),
        ('cgo', 'CGO'),
        ('coo', 'COO'),
        ('cpo', 'CPO'),
        ('cfo', 'CFO'),
        ('ceo', 'CEO')
    ], string='Superior Level', required=True)

    active = fields.Boolean(default=True)

    manager_level_rank = fields.Integer(string='Manager Level Rank', compute='_compute_level_ranks', store=True)
    superior_level_rank = fields.Integer(string='Superior Level Rank', compute='_compute_level_ranks', store=True)

    
    @api.depends('manager_level', 'superior_level')
    def _compute_level_ranks(self):
        level_map = {
            'dept_supv': 1,
            'dept_mgr': 2,
            'prog_mgr': 3,
            'safety_mgr': 4,
            'it_mgr': 5,
            'sc_mgr': 6,
            'dept_dir': 7,
            'gm_coo': 8,
            'cto': 9,
            'cgo': 10,
            'coo': 11,
            'cpo': 12,
            'cfo': 13,
            'ceo': 14
        }
        
        for record in self:
            record.manager_level_rank = level_map.get(record.manager_level, 0)
            record.superior_level_rank = level_map.get(record.superior_level, 0)

    _sql_constraints = [
        ('unique_user_manager_level', 'unique(user_id, manager_level)', 
         'This user is already an approver for that manager level!')
    ]

    def name_get(self):
        return [(record.id, record.user_id.name) for record in self]