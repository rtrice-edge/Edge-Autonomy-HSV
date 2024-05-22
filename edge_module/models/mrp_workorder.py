from odoo import api, fields, models

class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'


    production_user_id = fields.Many2one('res.users', related='production_id.user_id', string='MO Responsible', store=True)
  
    quality_check_id = fields.Many2one('quality.check', compute='_compute_quality_check_id', string='Quality Check')

    def _compute_quality_check_id(self):
        for workorder in self:
            quality_check = self.env['quality.check'].search([('workorder_id', '=', workorder.id)], limit=1)
            workorder.quality_check_id = quality_check
            
            #sooooooon
    def open_quality_check(self):
        self.ensure_one()
        action = self.env.ref('quality_control.quality_check_action_main').read()[0]
        action['views'] = [(self.env.ref('quality_control.quality_check_view_form').id, 'form')]
        action['res_id'] = self.id
        action['target'] = 'new'
        return action