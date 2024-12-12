from odoo import models, api, fields

class MrpBom(models.Model):
    _inherit = 'mrp.bom.line'

    notes = fields.Text(string='Notes')
    product_type = fields.Selection(related='product_id.type', string='Component Type', readonly=True)
    sort_code = fields.Selection([('stockroom', 'Stockroom'), ('kanban', 'Kanban'), ('free_stock', "Free Stock"), ("consumables", "Consumables")], string='Sort Code')