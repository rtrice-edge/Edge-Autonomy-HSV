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
    

    def write(self, vals):
        _logger.info(f"Before write: {self.order_line.mapped('name')}")
        res = super(PurchaseOrder, self).write(vals)
        _logger.info(f"After write: {self.order_line.mapped('name')}")
        return res
    def create(self, vals):
        _logger.info("Before create: %s", vals.get('order_line', []))
        res = super(PurchaseOrder, self).create(vals)
        _logger.info("After create: %s", res.order_line.mapped('name'))
        return res
 
    @api.model
    def _get_project_names(self):
        projects = self.env['project.project'].search([('active', '=', True)])
        return [(project.name, project.name) for project in projects]
    


    po_vendor_terms = fields.Char(string='Vendor Terms', readonly='True')

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
            if self.partner_id:
                    self.po_vendor_terms = self.partner_id.vendor_terms

    @api.model
    def create(self, vals):
            res = super(Purchaseorder, self).create(vals)
            return res


    # # This method is called to pull over the custom descriptions onto the RFQ
    # @api.model
    # def create(self, vals):
    #     _logger.info('Called create Purchase Order')
    #     if vals.get('requisition_id'):
    #         _logger.info('There was a requisition_id in the vals')
    #         requisition = self.env['purchase.requisition'].browse(vals['requisition_id'])
    #         _logger.info(requisition)
    #         if requisition:
    #             for line in requisition.line_ids:
    #                 _logger.info(line)
    #                 for order_line in vals.get('order_line', []):
    #                     if order_line[2]['product_id'] == line.product_id.id:
    #                         order_line[2]['name'] = line.product_description_variants
    #     return super(PurchaseOrder, self).create(vals)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
 
    def action_view_picking(self):
        action = super(PurchaseOrder, self).action_view_picking()
        if self.state != 'done':
            if 'print' in action.get('context', {}).get('default_print'):
                action['context']['default_print'].remove('print')
        return action