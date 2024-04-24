from odoo import models, api, fields

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    tracking_number = fields.Char(string='Tracking Number')
    carrier = fields.Char(string='Carrier')
    currency_id = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True)
    delivery_price = fields.Monetary('Delivery Cost', currency_field='currency_id', default=0.0)
    
    clickable_url = fields.Char(string='Clickable URL', compute='_compute_clickable_url')

    @api.depends('name')
    def _compute_clickable_url(self):
        for record in self:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            record.clickable_url = f'{base_url}/web#id={record.id}&model=stock.picking&view_type=form'