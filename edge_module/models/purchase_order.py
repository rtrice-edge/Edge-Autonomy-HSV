from odoo import models, fields, api

import logging
_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    urgency = fields.Selection(
        [
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('stoppage', 'Stoppage'),
        ],
        string='Urgency',
        default='low',
    )
    project_name = fields.Selection(selection='_get_project_names', string='Project')
    shipping_method = fields.Char(string='Shipping Method')
    
    po_vendor_terms = fields.Char(string='Vendor Terms')

    edge_recipient = fields.Char(string='Edge Recipient')

    edge_contact = fields.Selection(selection='_get_purchasing_users', string='Edge Contact', default=lambda self: self.env.user.id)

    procurement_user_id = fields.Many2one('hr.employee', string='Procurement User', domain=lambda self: self._get_purchase_user_ids())
    


 
    @api.model
    def _get_project_names(self):
        projects = self.env['project.project'].search([('active', '=', True)])
        return [(project.name, project.name) for project in projects]

    def _get_purchase_user_ids(self):
    purchase_user_group = self.env.ref('purchase.group_purchase_user')
    if purchase_user_group:
        user_ids = purchase_user_group.users.ids
        return [('id', 'in', user_ids)]
    return []

    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        _logger.info('Called onchange partner_id')
        if self.partner_id:
            self.po_vendor_terms = self.partner_id.vendor_terms
        if self.requisition_id:
            _logger.info('There was a requisition_id in the vals')
            requisition = self.env['purchase.requisition'].browse(self.requisition_id.id)
            _logger.info(requisition)
            if requisition:
                for i, line in enumerate(requisition.line_ids):
                    _logger.info(line.product_description_variants)
                    if i < len(self.order_line):
                        _logger.info("I'm in the loop!")
                        _logger.info(self.order_line[i].name)
                        self.order_line[i].name = line.product_description_variants
                        _logger.info(self.order_line[i].name)
        
        
    
    @api.model
    def create(self, vals):
        res = super(PurchaseOrder, self).create(vals)
        res.po_vendor_terms = res.partner_id.vendor_terms
        return res

    # @api.model_create_multi
    # def create(self, vals):
    #     _logger.info('Called create Purchase Order')
    #     _logger.info(vals)
    #     if vals.get('requisition_id'):
    #         _logger.info('There was a requisition_id in the vals')
    #         requisition = self.env['purchase.requisition'].browse(vals['requisition_id'])
    #         _logger.info(requisition)
    #         if requisition:
    #             for line in requisition.line_ids:
    #                 _logger.info(line)
    #                 for order_line in vals.get('order_line', []):
    #                     _logger.info(order_line)
    #                     order_line['name'] = line.product_description_variants
    #     return super(PurchaseOrder, self).create(vals)
