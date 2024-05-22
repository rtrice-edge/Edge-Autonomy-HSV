from odoo import api, models, fields

class QualityCheck(models.Model):
    _inherit = 'quality.check'
    production_id = fields.Many2one('mrp.production', string='Manufacturing Order', compute='_compute_production_id')

    @api.depends('product_id', 'lot_id', 'picking_id')
    def _compute_production_id(self):
        for check in self:
            production = False
            if check.picking_id:
                production = self.env['mrp.production'].search([('picking_ids', 'in', check.picking_id.id)], limit=1)
            elif check.lot_id:
                production = self.env['mrp.production'].search([('finished_move_line_ids.lot_id', '=', check.lot_id.id)], limit=1)
            check.production_id = production
    

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