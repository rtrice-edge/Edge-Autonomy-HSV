from odoo import api, fields, models

class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    quality_check_ids = fields.One2many('quality.check', compute='_compute_quality_check_ids', string='Quality Checks')

  
    def _compute_quality_check_ids(self):
        for workorder in self:
            quality_checks = self.env['quality.check'].search([('workorder_id', '=', workorder.id)])
            workorder.quality_check_ids = quality_checks
            
            #sooooooon
    def open_quality_check(self):
        self.ensure_one()
        action = self.env.ref('quality_control.quality_check_action_main').read()[0]
        action['views'] = [(self.env.ref('quality_control.quality_check_view_form').id, 'form')]
        action['res_id'] = self.id
        action['target'] = 'new'
        return action