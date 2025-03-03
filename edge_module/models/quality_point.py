from odoo import models, fields

class QualityPoint(models.Model):
    _inherit = 'quality.point'
    
    outcome_verbiage = fields.Selection(
        [
            ('pass_fail', 'Pass/Fail'),
            ('complete', 'Complete/Not Complete'),
        ],
        string="Outcome Verbiage",
        default='pass_fail',
        required=True,
    )