#odoo procurement category

from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    vendornumber = fields.char(string='Vendor Number', required=True)