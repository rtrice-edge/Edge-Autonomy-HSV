from odoo import models, fields, api, _
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)

class MrpWorkorder(models.Model):
    _name = 'mrp.workorder'
    _inherit = ['mrp.workorder', 'mail.thread', 'mail.activity.mixin']

    message_ids = fields.One2many('mail.message', 'res_id', string='Messages', domain=lambda self: [('model', '=', self._name)], auto_join=True)

    production_user_id = fields.Many2one('res.users', related='production_id.user_id', string='MO Responsible', store=True)
    
  
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
                    
    def _create_consumable_lot_lines(self):
        for workorder in self:
            existing_products = workorder.consumable_lot_ids.mapped('product_id')
            consumables = workorder.production_id.bom_id.bom_line_ids.filtered(
                lambda l: l.product_id.type == 'consu' and 
                          l.product_id not in existing_products and 
                          l.operation_id == workorder.operation_id
            ).mapped('product_id')
            for consumable in consumables:
                self.env['mrp.workorder.consumable.lot'].create({
                    'workorder_id': workorder.id,
                    'product_id': consumable.id,
                })

    @api.model
    def create(self, vals):
        workorder = super(MrpWorkorder, self).create(vals)
        workorder._create_consumable_lot_lines()
        return workorder

    def button_finish(self):
        for workorder in self:
            if any(not lot.lot_id or not lot.expiration_date for lot in workorder.consumable_lot_ids):
                raise UserError(_("Please fill out lot and expiration date for all consumables before finishing the work order."))
        return super(MrpWorkorder, self).button_finish()
    
    def button_start(self):
        """Override the start button method to add validation"""
        self.ensure_one()
        _logger.info(
            'button_start called for Work Order ID: %s\nState: %s\nProduction State: %s\nWorking State: %s', 
            self.id, 
            self.state,
            self.production_state,
            self.working_state
        )
        self.ensure_one()
        if self.state == 'pending':
            raise UserError(_("Cannot start this work order because it is waiting for another work order to complete."))
        if self.state == 'done':
            raise UserError(_("Cannot start a completed work order."))
        return super(MrpWorkorder, self).button_start()

    def button_block(self):
        """Override the block button method to add validation"""
        self.ensure_one()
        if self.state == 'pending':
            raise UserError(_("Cannot block this work order because it is waiting for another work order."))
        if self.state == 'done':
            raise UserError(_("Cannot block a completed work order."))
        return super(MrpWorkorder, self).button_block()

class MrpWorkorderConsumableLot(models.Model):
    _name = 'mrp.workorder.consumable.lot'
    _description = 'Work Order Consumable Lot'

    workorder_id = fields.Many2one('mrp.workorder', string='Work Order', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Consumable Product', required=True, readonly=True)
    lot_id = fields.Char(string='Lot/Serial Number')
    expiration_date = fields.Date(string='Expiration Date')


