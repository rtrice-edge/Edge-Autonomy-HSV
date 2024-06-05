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
        help="Select the urgency level of this item. 'Stoppage' indicates a critical issue that halts operations."
    )
    project_name = fields.Selection(selection='_get_project_names', string='Project', help="Select the project that this purchase should be charged to. Find and edit the list of projects in the projects tab.")
    shipping_method = fields.Char(string='Shipping Method', help="Please input the carrier or shipping method for this purchase.")
    
    po_vendor_terms = fields.Char(string='Vendor Terms', help="This field will be automatically populated with any existing terms for the venor. If none exist, this will be empty. An example is NET30.")

    edge_recipient_new = fields.Many2one('hr.employee', string='Internal Recipient', help="This is where you select the person who the package is to be delivered to when it enters the facility. This defailts as the person who created the purchase request.", default="user_id")

    #purchase_contact = fields.Many2one('hr.employee', string='Edge Contact')


 
    @api.model
    def _get_project_names(self):
        projects = self.env['project.project'].search([('active', '=', True)])
        return [(project.name, project.name) for project in projects]


    
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
