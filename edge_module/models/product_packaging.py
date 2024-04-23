from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)

class ProductPackaging(models.Model):
    _inherit = 'product.packaging'

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id', readonly=True)
    package_price = fields.Monetary('Package Price', currency_field='currency_id', default=0.0)