from odoo import models, fields, api


import logging
_logger = logging.getLogger(__name__)

class ProductPackaging(models.Model):
    _inherit = 'product.packaging'

    currency_id = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True)
    package_price = fields.Monetary('Package Price', currency_field='currency_id', default=0.0)