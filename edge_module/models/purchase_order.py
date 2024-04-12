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
    vendorterms = fields.Char(string='Vendor Terms')
 
    @api.model
    def _get_project_names(self):
        projects = self.env['project.project'].search([('active', '=', True)])
        return [(project.name, project.name) for project in projects]
    

    @api.onchange('partner_id')
    def _onchange_partner(self):
        for line in self.order_line:
            line._update_vendor_number()
    # This method is called to pull over the custom descriptions onto the RFQ
    @api.model
    def create(self, vals):
        _logger.info('Called create Purchase Order')
        if vals.get('requisition_id'):
            _logger.info('There was a requisition_id in the vals')
            requisition = self.env['purchase.requisition'].browse(vals['requisition_id'])
            _logger.info(requisition)
            
            if requisition:
                for line in requisition.line_ids:
                    _logger.info('in the loop for line_ids')
                    _logger.info(line)
                    for order_line in vals.get('order_line', []):
                        if order_line[2]['product_id'] == line.product_id.id:
                            order_line[2]['name'] = line.product_description_variants
        return super(PurchaseOrder, self).create(vals)