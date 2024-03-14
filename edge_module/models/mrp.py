from odoo import models, api, fields

class MrpBom(models.Model):
    _inherit = 'mrp.bom.line'

    notes = fields.Text(string='Notes')