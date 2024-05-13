from odoo import models, fields, api, tools

class ComponentMOView(models.Model):
    _name = 'component.mo.view'
    _rec_name = 'product_id'
    _auto = False
    _description = 'Component MO View'

    id = fields.Integer(string='ID', readonly=True)
    product_id = fields.Many2one('product.product', string='Product')
    product_code = fields.Char(string='Product Code')
    product_name = fields.Char(string='Product Name')
    mo_id = fields.Many2one('mrp.production', string='Manufacturing Order')
    mo_name = fields.Char(string='Manufacturing Order Name')
    mo_quantity = fields.Float(string='Manufacturing Order Quantity')
    component_quantity = fields.Float(string='Component Quantity')
    mo_month = fields.Char(string='MO Month')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
           CREATE VIEW component_mo_view AS
                SELECT
                    ROW_NUMBER() OVER (ORDER BY p.id, mo.id) AS id,
                    p.id AS product_id,
                    p.default_code AS product_code,
                    pt.name->>'en_US' AS product_name,
                    mo.id AS mo_id,
                    mo.name AS mo_name,
                    mo.product_qty AS mo_quantity,
                    SUM(sm.product_uom_qty) AS component_quantity,
                    TO_CHAR(mo.date_start, 'YYYY-MM') AS mo_month
                FROM
                    mrp_production mo
                    JOIN stock_move sm ON mo.id = sm.raw_material_production_id
                    JOIN product_product p ON sm.product_id = p.id
                    JOIN product_template pt ON p.product_tmpl_id = pt.id
                WHERE
                    mo.state = 'confirmed'
                GROUP BY
                    p.id, pt.name, mo.id, mo.name, mo.product_qty, mo.date_start
                ORDER BY
                    mo.date_start, p.id, mo.id;

        """)
