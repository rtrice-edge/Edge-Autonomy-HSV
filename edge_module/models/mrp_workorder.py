from odoo import api, fields, models

class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    quality_check_ids = fields.One2many('quality.check', 'workorder_id', string='Quality Checks')
    quality_check_count = fields.Integer(compute='_compute_quality_check_count', string='Quality Check Count')
    invisible_button = fields.Boolean(compute='_compute_invisible_button')

    @api.depends('quality_check_ids')
    def _compute_quality_check_count(self):
        for workorder in self:
            workorder.quality_check_count = len(workorder.quality_check_ids)

    @api.depends('quality_check_ids')
    def _compute_invisible_button(self):
        for workorder in self:
            workorder.invisible_button = not bool(workorder.quality_check_ids)

    def action_view_quality_checks(self):
        self.ensure_one()
        action = self.env.ref('quality_control.quality_check_action_main').read()[0]
        action['domain'] = [('id', 'in', self.quality_check_ids.ids)]
        return action