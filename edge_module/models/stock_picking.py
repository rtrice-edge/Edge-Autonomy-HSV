from odoo import models, api, fields

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    tracking_number = fields.Char(string='Tracking Number')
    carrier = fields.Char(string='Carrier')
    currency_id = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True)
    delivery_price = fields.Monetary('Delivery Cost', currency_field='currency_id', default=0.0)
    
    clickable_url = fields.Char(string='Clickable URL', compute='_compute_clickable_url')
    
    mo_product_id = fields.Many2one('product.product', string='MO Product', compute='_compute_mo_product_id')

    @api.depends('mo_id')
    def _compute_mo_product_id(self):
        for picking in self:
            if picking.mo_id:
                picking.mo_product_id = picking.mo_id.product_id
            else:
                picking.mo_product_id = False
    

    @api.depends('name')
    def _compute_clickable_url(self):
        for record in self:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            record.clickable_url = f'{base_url}/web#id={record.id}&cids=1&menu_id=202&action=372&&model=stock.picking&view_type=form'