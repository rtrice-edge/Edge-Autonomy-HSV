from odoo import api, fields, models

class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    quality_check_ids = fields.One2many('quality.check', compute='_compute_quality_check_ids', string='Quality Checks')

  
    def _compute_quality_check_ids(self):
        for workorder in self:
            quality_checks = self.env['quality.check'].search([('workorder_id', '=', workorder.id)])
            workorder.quality_check_ids = quality_checks