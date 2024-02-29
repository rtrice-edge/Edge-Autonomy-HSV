#odoo procurement category

from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    vendornumber = fields.Char('Vendor Number', required=True)