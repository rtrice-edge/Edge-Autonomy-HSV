from odoo import api, models

class QualityCheck(models.Model):
    _inherit = 'quality.check'

    def open_quality_check(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Quality Check',
            'view_mode': 'form',
            'res_model': 'quality.check',
            'res_id': self.id,
            'target': 'new',
            'context': self.env.context,
        }