from odoo import api, models, fields

class QualityCheck(models.Model):
    _inherit = 'quality.check'
    
    # worksheet_document = fields.Binary(related='point_id.worksheet_document', readonly=True)
    # quality_state = fields.Selection([
    #      ('none', 'None'),
    #      ('pass', 'Pass'),
    #      ('fail', 'Fail'),
    #      ('complete', 'Complete'),
    #      ('not_complete', 'Not Complete'),
    # ], string="Quality State", default='none')
    
    # outcome_type = fields.Selection(
    #     [('pass_fail', 'Pass/Fail'), ('complete', 'Complete/Not Complete')],
    #     string='Outcome Type',
    #     compute='_compute_outcome_type',
    #     store=True,
    # )

    # @api.depends('point_id.outcome_verbiage')
    # def _compute_outcome_type(self):
    #     for rec in self:
    #         rec.outcome_type = rec.point_id.outcome_verbiage or 'pass_fail'
    
    # def do_pass(self):
    #     self.write({'quality_state': 'pass'})
    #     self.message_post(body="Quality Check marked as Pass.")
    
    # def do_fail(self):
    #     self.write({'quality_state': 'fail'})
    #     self.message_post(body="Quality Check marked as Fail.")
    
    # def do_complete(self):
    #     self.write({'quality_state': 'complete'})
    #     self.message_post(body="Quality Check marked as Complete.")
    
    # def do_not_complete(self):
    #     self.write({'quality_state': 'not_complete'})
    #     self.message_post(body="Quality Check marked as Not Complete.")
    
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