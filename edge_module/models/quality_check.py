from odoo import api, models, fields

class QualityCheck(models.Model):
    _inherit = 'quality.check'
    
    worksheet_document = fields.Binary(related='point_id.worksheet_document', readonly=True)
    quality_state = fields.Selection(
        [('none', 'None'),
         ('pass', 'Complete'),  # Changed label from "Pass" to "Complete"
         ('fail', 'Fail')],
        string="Quality State",
        default='none'
    )

    worksheet_document = fields.Binary(related='point_id.worksheet_document', readonly=True)
    
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