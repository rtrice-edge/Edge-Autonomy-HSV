from odoo import models, fields, api, tools
import math

class Demand(models.Model):
    _name = 'demand.model'
    _description = 'Demand Model'
    _rec_name = 'component_code'
    _auto = False
    
    id = fields.Integer(string='ID', required=True, readonly=True, index=True)
    component_code = fields.Char(string='Component Code', required=False, readonly=True)
    component_name = fields.Char(string='Component Name', required=False, readonly=True)
    is_storable    = fields.Char(string='Is Storable', required=False, readonly=True)
    in_stock = fields.Float(string='In Stock', required=False, readonly=True)
    on_order = fields.Float(string='On Order', required=False, readonly=True)
    month_1  = fields.Float(string='Month 1', required=False, readonly=True, digits=(10, 2))
    month_2  = fields.Float(string='Month 2', required=False, readonly=True)
    month_3  = fields.Float(string='Month 3', required=False, readonly=True)
    month_4  = fields.Float(string='Month 4', required=False, readonly=True)
    month_5  = fields.Float(string='Month 5', required=False, readonly=True)
    month_6  = fields.Float(string='Month 6', required=False, readonly=True)
    month_7  = fields.Float(string='Month 7', required=False, readonly=True)
    month_8  = fields.Float(string='Month 8', required=False, readonly=True)
    
    mon_1_val_1 = fields.Float(compute='_compute_values', string='Month 1 Value 1', store=False)
    mon_1_val_2 = fields.Float(compute='_compute_values', string='Month 1 Value 2', store=False)
    mon_2_val_1 = fields.Float(compute='_compute_values', string='Month 2 Value 1', store=False)
    mon_2_val_2 = fields.Float(compute='_compute_values', string='Month 2 Value 2', store=False)
    mon_3_val_1 = fields.Float(compute='_compute_values', string='Month 3 Value 1', store=False)
    mon_3_val_2 = fields.Float(compute='_compute_values', string='Month 3 Value 2', store=False)
    mon_4_val_1 = fields.Float(compute='_compute_values', string='Month 4 Value 1', store=False)
    mon_4_val_2 = fields.Float(compute='_compute_values', string='Month 4 Value 2', store=False)
    mon_5_val_1 = fields.Float(compute='_compute_values', string='Month 5 Value 1', store=False)
    mon_5_val_2 = fields.Float(compute='_compute_values', string='Month 5 Value 2', store=False)
    mon_6_val_1 = fields.Float(compute='_compute_values', string='Month 6 Value 1', store=False)
    mon_6_val_2 = fields.Float(compute='_compute_values', string='Month 6 Value 2', store=False)
    mon_7_val_1 = fields.Float(compute='_compute_values', string='Month 7 Value 1', store=False)
    mon_7_val_2 = fields.Float(compute='_compute_values', string='Month 7 Value 2', store=False)
    mon_8_val_1 = fields.Float(compute='_compute_values', string='Month 8 Value 1', store=False)
    mon_8_val_2 = fields.Float(compute='_compute_values', string='Month 8 Value 2', store=False)
    mon_1       = fields.Html(compute='_compute_values', string='Month 1', store=False)
    
    @api.depends('in_stock', 'on_order')
    def _compute_values(self):
        for record in self:
            record.mon_1_val_1 = math.ceil(record.in_stock - record.month_1)
            record.mon_1_val_2 = math.ceil(record.in_stock + record.on_order - record.month_1)
            record.mon_2_val_1 = math.ceil(record.in_stock - record.month_1 - record.month_2)
            record.mon_2_val_2 = math.ceil(record.in_stock + record.on_order - record.month_1 - record.month_2)
            record.mon_3_val_1 = math.ceil(record.in_stock - record.month_1 - record.month_2 - record.month_3)
            record.mon_3_val_2 = math.ceil(record.in_stock + record.on_order - record.month_1 - record.month_2 - record.month_3)
            record.mon_4_val_1 = math.ceil(record.in_stock - record.month_1 - record.month_2 - record.month_3 - record.month_4)
            record.mon_4_val_2 = math.ceil(record.in_stock + record.on_order - record.month_1 - record.month_2 - record.month_3 - record.month_4)
            record.mon_5_val_1 = math.ceil(record.in_stock - record.month_1 - record.month_2 - record.month_3 - record.month_4 - record.month_5)
            record.mon_5_val_2 = math.ceil(record.in_stock + record.on_order - record.month_1 - record.month_2 - record.month_3 - record.month_4 - record.month_5)
            record.mon_6_val_1 = math.ceil(record.in_stock - record.month_1 - record.month_2 - record.month_3 - record.month_4 - record.month_5 - record.month_6)
            record.mon_6_val_2 = math.ceil(record.in_stock + record.on_order - record.month_1 - record.month_2 - record.month_3 - record.month_4 - record.month_5 - record.month_6)
            record.mon_7_val_1 = math.ceil(record.in_stock - record.month_1 - record.month_2 - record.month_3 - record.month_4 - record.month_5 - record.month_6 - record.month_7)
            record.mon_7_val_2 = math.ceil(record.in_stock + record.on_order - record.month_1 - record.month_2 - record.month_3 - record.month_4 - record.month_5 - record.month_6 - record.month_7)
            record.mon_8_val_1 = math.ceil(record.in_stock - record.month_1 - record.month_2 - record.month_3 - record.month_4 - record.month_5 - record.month_6 - record.month_7 - record.month_8)
            record.mon_8_val_2 = math.ceil(record.in_stock + record.on_order - record.month_1 - record.month_2 - record.month_3 - record.month_4 - record.month_5 - record.month_6 - record.month_7 - record.month_8)
            # I want to display the values in a human-readable format
            # I also want negative values to be displayed in red
            record.mon_1 = f'{record.month_1} (<span style="color: {"red" if record.mon_1_val_1 < 0 else "green"}">{record.mon_1_val_1}</span>/<span style="color: {"red" if record.mon_1_val_2 < 0 else "green"}">{record.mon_1_val_2}</span>)'
    
    def init(self):
        #This is a test
        # tools.drop_view_if_exists(self.env.cr, self._table)
        self._cr.execute("""
                         CREATE OR REPLACE VIEW demand_model AS (
                         WITH inventory_on_order AS (
                            SELECT
                                pp.id AS product_id,
                                COALESCE(inventory.on_hand_quantity, 0) AS "In Inventory",
                                COALESCE(on_order.on_order_quantity, 0) AS "On Order"
                            FROM
                                product_product pp
                            LEFT JOIN
                                (
                                    SELECT
                                        pp.id AS product_id,
                                        SUM(sq.quantity) AS on_hand_quantity
                                    FROM
                                        stock_quant sq
                                    JOIN
                                        stock_location sl ON sq.location_id = sl.id
                                    JOIN
                                        product_product pp ON sq.product_id = pp.id
                                    WHERE
                                        sl.complete_name NOT LIKE 'Virtual Locations/%' -- Exclude virtual locations
                                        AND sl.complete_name NOT LIKE 'Partners/%' -- Exclude partner locations
                                    GROUP BY
                                        pp.id
                                ) inventory ON pp.id = inventory.product_id
                            LEFT JOIN
                                (
                                    SELECT
                                        pp.id AS product_id,
                                        SUM(pol.product_qty - pol.qty_received) AS on_order_quantity
                                    FROM
                                        purchase_order_line pol
                                    JOIN
                                        product_product pp ON pol.product_id = pp.id
                                    JOIN
                                        purchase_order po ON pol.order_id = po.id
                                    WHERE
                                        po.state IN ('draft', 'sent', 'to approve', 'purchase', 'done') -- Include 'done' state
                                    GROUP BY
                                        pp.id
                                ) on_order ON pp.id = on_order.product_id
                        ),
                        months AS (
                            SELECT DISTINCT DATE_TRUNC('month', mo.date_start)::DATE AS month
                            FROM mrp_production mo
                            WHERE mo.state IN ('draft', 'confirmed', 'progress')
                            UNION
                            SELECT GENERATE_SERIES(
                                (SELECT MIN(DATE_TRUNC('month', date_start)::DATE) FROM mrp_production WHERE state IN ('draft', 'confirmed', 'progress')),
                                (SELECT MIN(DATE_TRUNC('month', date_start)::DATE) FROM mrp_production WHERE state IN ('draft', 'confirmed', 'progress')) + INTERVAL '7 months',
                                INTERVAL '1 month'
                            )
                        )
                        SELECT
                            mobl.product_id AS id,
                            p.default_code AS component_code,
                            pt.name->>'en_US' AS component_name,
                            CASE WHEN pt.type = 'product' THEN 'Yes' ELSE 'No' END AS is_storable,
                            COALESCE(io."In Inventory", 0) AS "in_stock",
                            COALESCE(io."On Order", 0) AS "on_order",
                            SUM(
                                CASE
                                    WHEN uom.name->>'en_US' = 'in' THEN mobl.product_qty * mo.product_qty / 12
                                    ELSE mobl.product_qty * mo.product_qty
                                END
                            ) FILTER (WHERE DATE_TRUNC('month', mo.date_start)::DATE = m.month) AS month_1,
                            SUM(
                                CASE
                                    WHEN uom.name->>'en_US' = 'in' THEN mobl.product_qty * mo.product_qty / 12
                                    ELSE mobl.product_qty * mo.product_qty
                                END
                            ) FILTER (WHERE DATE_TRUNC('month', mo.date_start)::DATE = m.month + INTERVAL '1 month') AS month_2,
                            SUM(
                                CASE
                                    WHEN uom.name->>'en_US' = 'in' THEN mobl.product_qty * mo.product_qty / 12
                                    ELSE mobl.product_qty * mo.product_qty
                                END
                            ) FILTER (WHERE DATE_TRUNC('month', mo.date_start)::DATE = m.month + INTERVAL '2 months') AS month_3,
                            SUM(
                                CASE
                                    WHEN uom.name->>'en_US' = 'in' THEN mobl.product_qty * mo.product_qty / 12
                                    ELSE mobl.product_qty * mo.product_qty
                                END
                            ) FILTER (WHERE DATE_TRUNC('month', mo.date_start)::DATE = m.month + INTERVAL '3 months') AS month_4,
                            SUM(
                                CASE
                                    WHEN uom.name->>'en_US' = 'in' THEN mobl.product_qty * mo.product_qty / 12
                                    ELSE mobl.product_qty * mo.product_qty
                                END
                            ) FILTER (WHERE DATE_TRUNC('month', mo.date_start)::DATE = m.month + INTERVAL '4 months') AS month_5,
                            SUM(
                                CASE
                                    WHEN uom.name->>'en_US' = 'in' THEN mobl.product_qty * mo.product_qty / 12
                                    ELSE mobl.product_qty * mo.product_qty
                                END
                            ) FILTER (WHERE DATE_TRUNC('month', mo.date_start)::DATE = m.month + INTERVAL '5 months') AS month_6,
                            SUM(
                                CASE
                                    WHEN uom.name->>'en_US' = 'in' THEN mobl.product_qty * mo.product_qty / 12
                                    ELSE mobl.product_qty * mo.product_qty
                                END
                            ) FILTER (WHERE DATE_TRUNC('month', mo.date_start)::DATE = m.month + INTERVAL '6 months') AS month_7,
                            SUM(
                                CASE
                                    WHEN uom.name->>'en_US' = 'in' THEN mobl.product_qty * mo.product_qty / 12
                                    ELSE mobl.product_qty * mo.product_qty
                                END
                            ) FILTER (WHERE DATE_TRUNC('month', mo.date_start)::DATE = m.month + INTERVAL '7 months') AS month_8
                        FROM
                            months m
                        CROSS JOIN
                            mrp_bom_line mobl
                        JOIN
                            mrp_bom mb ON mobl.bom_id = mb.id
                        JOIN
                            mrp_production mo ON mb.id = mo.bom_id AND mo.state IN ('draft', 'confirmed', 'progress')
                        JOIN
                            product_product p ON mobl.product_id = p.id
                        JOIN
                            product_template pt ON p.product_tmpl_id = pt.id
                        JOIN
                            uom_uom uom ON mobl.product_uom_id = uom.id
                        LEFT JOIN
                            inventory_on_order io ON p.id = io.product_id
                        GROUP BY
                            mobl.product_id,
                            p.default_code,
                            pt.name,
                            pt.type,
                            io."In Inventory",
                            io."On Order")    """ )