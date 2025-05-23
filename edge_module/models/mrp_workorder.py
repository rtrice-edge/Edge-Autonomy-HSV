from odoo import models, fields, api, _
from odoo.exceptions import UserError
import re
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class MrpWorkorder(models.Model):
    _name = 'mrp.workorder'
    _inherit = ['mrp.workorder', 'mail.thread', 'mail.activity.mixin']

    message_ids = fields.One2many('mail.message', 'res_id', string='Messages', domain=lambda self: [('model', '=', self._name)], auto_join=True)

    production_user_id = fields.Many2one('res.users', related='production_id.user_id', string='MO Responsible', store=True)
    
  
    quality_check_id = fields.Many2one('quality.check', compute='_compute_quality_check_id', string='Quality Check')
    
    consumable_lot_ids = fields.One2many('mrp.workorder.consumable.lot', 'workorder_id', string='Consumable Lots')
    
    
    #### lets get some order up in here.
    _order = 'sequence_number'  # This will be our new sorting field

    sequence_number = fields.Integer(
        string='Sequence Number',
        compute='_compute_sequence_number',
        store=True
    )

    @api.depends('name')
    def _compute_sequence_number(self):
        for workorder in self:
            # Extract the first number from the name
            match = re.match(r'^(\d+)', workorder.name or '')
            workorder.sequence_number = int(match.group(1)) if match else 999999  # Default high number for non-matching names

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
        #Log the current state of the workorder
        _logger.info(
            'reset_operation called for Work Order ID: %s\nState: %s\nProduction State: %s\nWorking State: %s', 
            self.id, 
            self.state,
            self.production_state,
            self.working_state
        )
        for workorder in self:
            #If the workorder is in the pending state, we can reset it to ready
            # we also want to check to see if the work_order is in progress
            if (workorder.state == 'ready') | (workorder.state == 'progress'):
                #If the workorder is ready, we can reset it to pending
                #log the state change
                _logger.info('Work Order ID: %s reset to pending', workorder.id)
                workorder.write({'state': 'pending'})
                #If the workorder is in progress, we can reset it to ready
                
                previous_workorder = self.env['mrp.workorder'].search([('id', '=', workorder.id - 1), ('production_id', '=', workorder.production_id.id)], limit=1)
                #Log the previous workorder state and and number
                _logger.info('Previous Work Order ID: %s\nState: %s', previous_workorder.id, previous_workorder.state)
                if previous_workorder:
                    previous_workorder.write({'state': 'ready'})
                    _logger.info('Work Order ID: %s reset to ready', previous_workorder.id)
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
            # Check if the associated quality check exists and is in a failed state
            _logger.info('Quality Check ID: %s\nQuality State: %s', workorder.quality_check_id, workorder.quality_check_id.quality_state)
            
            if workorder.quality_check_id and workorder.quality_check_id.quality_state == 'fail':
                raise ValidationError(
                    _("You cannot mark this work order as done because the associated quality check has failed.")
                )

            # Ensure consumable lots have required details
            if any(not lot.lot_id and not lot.expiration_date for lot in workorder.consumable_lot_ids):
                raise UserError(_("Please fill out lot and expiration date for all consumables before finishing the work order."))
        return super(MrpWorkorder, self).button_finish()
    
    def button_done(self):
        for workorder in self:
            # Check if the associated quality check exists and is in a failed state
            _logger.info('Quality Check ID: %s\nQuality State: %s', workorder.quality_check_id, workorder.quality_check_id.quality_state)
            
            if workorder.quality_check_id and workorder.quality_check_id.quality_state == 'fail':
                raise ValidationError(
                    _("You cannot mark this work order as done because the associated quality check has failed.")
                )

            # Ensure consumable lots have required details
            incomplete_lots = workorder.consumable_lot_ids.filtered(
                lambda lot: not lot.lot_id and not lot.expiration_date
            )
            if incomplete_lots:
                raise ValidationError(
                    _("You cannot mark this work order as done because some consumable lots are incomplete.")
                )

        return super(MrpWorkorder, self).button_done()
    
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


    @api.constrains('lot_id', 'expiration_date')
    def _check_required_fields(self):
        for record in self:
            if not record.lot_id and not record.expiration_date:
                raise ValidationError(
                    _("All consumable lots must have a Lot/Serial Number and an Expiration Date.")
                )