from odoo import models, fields, api

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