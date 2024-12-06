from odoo import models, api, fields

class MrpBom(models.Model):
    _inherit = 'mrp.bom.line'

    notes = fields.Text(string='Notes')
    product_type = fields.Selection(related='product_id.type', string='Component Type', readonly=True)
    # a new kit field that will be used to identify if the product is a kit or not
    kit = fields.Boolean(string='Kit')