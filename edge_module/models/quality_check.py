from odoo import api, models, fields

class QualityCheck(models.Model):
    _inherit = 'quality.check'
    
    worksheet_document = fields.Binary(related='point_id.worksheet_document', readonly=True)
    quality_state = fields.Selection(
        selection_add=[('complete', 'Complete')], 
        ondelete={'complete': 'set default'}  # Fix: use 'set default' instead of an invalid string
    )
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