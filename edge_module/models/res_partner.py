from odoo import models, fields

import logging
_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    vendor_terms = fields.Char(string='Vendor Terms')
