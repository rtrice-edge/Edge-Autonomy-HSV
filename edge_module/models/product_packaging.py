from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)

class ProductPackaging(models.Model):
    _inherit = 'product.packaging'

    packaging_currency_id = fields.Many2one('res.currency', string='Packaging Currency', related='company_id.currency_id', readonly=True)
    package_price = fields.Monetary('Package Price', currency_field='packaging_currency_id', default=0.0)