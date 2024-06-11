from odoo import api, fields, models

class MrpWorkorder(models.Model):
    _name = 'mrp.workorder'
    _inherit = ['mrp.workorder', 'mail.thread', 'mail.activity.mixin']

    message_ids = fields.One2many('mail.message', 'res_id', string='Messages', domain=lambda self: [('model', '=', self._name)], auto_join=True)

    production_user_id = fields.Many2one('res.users', related='production_id.user_id', string='MO Responsible', store=True)
    
    planned_week = fields.Selection('Planned Week', related='production_id.planned_week', string='Planned Week', store=True)
  
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
    
    def reset_operation(self):
        for workorder in self:
            if workorder.state == 'progress':
                workorder.write({'state': 'pending'})
                previous_workorder = self.env['mrp.workorder'].search([('id', '=', workorder.id - 1), ('production_id', '=', workorder.production_id.id)], limit=1)
                if previous_workorder:
                    previous_workorder.write({'state': 'ready'})

