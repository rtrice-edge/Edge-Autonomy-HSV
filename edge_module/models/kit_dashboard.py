from odoo import models, fields, api, tools
from datetime import datetime, timedelta

class KitDashboard(models.Model):
    _name = 'kit.dashboard'
    _description = 'Kit Production Dashboard'
    _auto = False  # This model does not create a database table

    kit_code = fields.Many2one('product.product', string="Kit Code", readonly=True)
    month = fields.Date(string="Month", readonly=True)
    total_kits = fields.Integer(string="Total Kits", readonly=True) 
    total_parts = fields.Integer(string="Total Parts", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW {} AS (
                SELECT 
                    row_number() OVER () as id,
                    product_id.id as kit_code,
                    date_trunc('month', m.date_start) as month,
                    SUM(qty_producing) as total_kits,
                    SUM(move_raw_ids.product_uom_qty * m.qty_producing) as total_parts
                FROM mrp_production m
                LEFT JOIN product_product product_id ON product_id.id = m.product_id  
                LEFT JOIN stock_move move_raw_ids ON move_raw_ids.raw_material_production_id = m.id
                WHERE product_id.default_code LIKE '%-KIT'
                GROUP BY product_id.id, date_trunc('month', m.date_start)
            )
        """.format(self._table))