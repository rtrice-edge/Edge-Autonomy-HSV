from odoo import api, fields, models

class MrpWorkorder(models.Model):
    _name = 'mrp.workorder'
    _inherit = ['mrp.workorder', 'mail.thread', 'mail.activity.mixin']

    message_ids = fields.One2many('mail.message', 'res_id', string='Messages', domain=lambda self: [('model', '=', self._name)], auto_join=True)

    production_user_id = fields.Many2one('res.users', related='production_id.user_id', string='MO Responsible', store=True)
    
    planned_week = fields.Selection('Planned Week', related='production_id.planned_week', string='Planned Week', store=True)
  
    quality_check_id = fields.Many2one('quality.check', compute='_compute_quality_check_id', string='Quality Check')
    
    consumable_lot_ids = fields.One2many('mrp.workorder.consumable.lot', 'workorder_id', string='Consumable Lots')
    
    
    #assigned_user_id = fields.Many2one('res.users', string='Assigned User', track_visibility='onchange')
    
    #assigned_employee_id = fields.Many2one('hr.employee', string='Assigned Employee', related='production_id.user_id.employee_id', store=True)


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
            if workorder.state == 'ready':
                workorder.write({'state': 'pending'})
                previous_workorder = self.env['mrp.workorder'].search([('id', '=', workorder.id - 1), ('production_id', '=', workorder.production_id.id)], limit=1)
                if previous_workorder:
                    previous_workorder.write({'state': 'ready'})
                    
    @api.model
    def create(self, vals):
        workorder = super(MrpWorkorder, self).create(vals)
        workorder._create_consumable_lot_lines()
        return workorder

    def _create_consumable_lot_lines(self):
        for workorder in self:
            consumables = workorder.production_bom_id.bom_line_ids.filtered(lambda l: l.product_id.type == 'consu')
            for consumable in consumables:
                self.env['mrp.workorder.consumable.lot'].create({
                    'workorder_id': workorder.id,
                    'product_id': consumable.product_id.id,
                })
                    
                    
class MrpWorkorderConsumableLot(models.Model):
    _name = 'mrp.workorder.consumable.lot'
    _description = 'Work Order Consumable Lot'

    workorder_id = fields.Many2one('mrp.workorder', string='Work Order', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Consumable Product', required=True, domain=[('type', '=', 'consu')])
    lot_id = fields.Char(string='Lot/Serial Number')
    expiration_date = fields.Date(string='Expiration Date')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id and self.product_id not in self.workorder_id.production_bom_id.bom_line_ids.product_id:
            return {'warning': {
                'title': "Warning",
                'message': "This product is not in the bill of materials for this production order."
            }

