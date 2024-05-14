from odoo import models, fields, api, tools
import math
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class Demand(models.Model):
    _name = 'demand.model'
    _description = 'Demand Model'
    _rec_name = 'component_code'
    _auto = False
    _sql = True
    
    id =         fields.Integer( string='ID', required=True, readonly=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, readonly=True)
    component_code = fields.Char(string='Component Code', required=False, readonly=True)
    component_name = fields.Char(string='Component Name', required=False, readonly=True)
    is_storable = fields.Boolean(string='Consumable?', required=False, readonly=True)
    has_bom = fields.Boolean(string='Has BOM?', required=False, readonly=True)
    in_stock = fields.Float(string='In Stock', required=False, readonly=True)
    on_order = fields.Float(string='On Order', required=False, readonly=True)
    current_month = datetime.now().month
    for i in range(1, 9):
        month_field = 'month_{}'.format(i)
        month_name = datetime(datetime.now().year, current_month + i - 1, 1).strftime('%B')
        vars()[month_field] = fields.Float(string=month_name, required=False, readonly=True, digits=(10, 2))
    
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
    mon_2      = fields.Html(compute='_compute_values', string='Month 2', store=False)
    mon_3      = fields.Html(compute='_compute_values', string='Month 3', store=False)
    mon_4      = fields.Html(compute='_compute_values', string='Month 4', store=False)
    mon_5      = fields.Html(compute='_compute_values', string='Month 5', store=False)
    mon_6      = fields.Html(compute='_compute_values', string='Month 6', store=False)
    mon_7      = fields.Html(compute='_compute_values', string='Month 7', store=False)
    mon_8      = fields.Html(compute='_compute_values', string='Month 8', store=False)
    component_link = fields.Html(string='Component Link', compute='_compute_component_code', readonly=True)


 
    def _compute_component_code(self):
        for record in self:
                record.component_link =  '<a href="/component_mo_view/%s">%s</a>' % (record.product_id.id, record.component_code or '')
  
    
    def open_mo_list(self):
        self.ensure_one()
        product_id = self.product_id.id
        return {
            'type': 'ir.actions.act_url',
            'url': '/mo_list/%s' % product_id,
            'target': 'new',
        }

    def action_view_purchase_orders(self):
        self.ensure_one()

        # Find the product based on the default code
        product = self.env['product.product'].search([('default_code', '=', self.component_code)], limit=1)

        # Prepare the action
        action = self.env.ref('edge_module.action_demand_purchase_orders').read()[0]
        action['domain'] = [('product_id', '=', product.id)] if product else []
        action['context'] = {'search_default_product_id': product.id if product else False}


        return action
        # action['context'] = {
        #     'search_default_order_line.product_id.default_code': self.component_code,
        #     'search_default_state': 'draft,sent,to approve',
        #     'search_default_filters': 1
        #       # Set default product
        # }
        
        # return action

        # # Search for the product using the component_code
        # product = self.env['product.product'].search([('default_code', '=', self.component_code)])
        # if product:
        #     # Add a custom filter to search for the product in the purchase order lines
        #     _logger.info("I found the product %s", product   )
        #     action['domain'] = [('state', 'in', ['draft', 'sent', 'to approve']), ('product', 'contains', self.component_code)]
        #     #action['context'] = {'search_default_product_id': product.id, 'default_product_id': product.id}
        #     action['context'] = {
                
        #     }
        # else:
        #     _logger.info("I did not find the product %s", product   )
        #     # Handle the case when no product is found with the given component_code
        #     action['domain'] = [('id', '=', False)]  # Empty domain to show no records
        #     action['context'] = {}

        return action

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
            record.mon_1 = f'{math.ceil(record.month_1)} (<span style="color: {"red" if record.mon_1_val_1 < 0 else "green"}">{record.mon_1_val_1}</span>/<span style="color: {"red" if record.mon_1_val_2 < 0 else "green"}">{record.mon_1_val_2}</span>)'
            record.mon_2 = f'{math.ceil(record.month_2)} (<span style="color: {"red" if record.mon_2_val_1 < 0 else "green"}">{record.mon_2_val_1}</span>/<span style="color: {"red" if record.mon_2_val_2 < 0 else "green"}">{record.mon_2_val_2}</span>)'
            record.mon_3 = f'{math.ceil(record.month_3)} (<span style="color: {"red" if record.mon_3_val_1 < 0 else "green"}">{record.mon_3_val_1}</span>/<span style="color: {"red" if record.mon_3_val_2 < 0 else "green"}">{record.mon_3_val_2}</span>)'
            record.mon_4 = f'{math.ceil(record.month_4)} (<span style="color: {"red" if record.mon_4_val_1 < 0 else "green"}">{record.mon_4_val_1}</span>/<span style="color: {"red" if record.mon_4_val_2 < 0 else "green"}">{record.mon_4_val_2}</span>)'
            record.mon_5 = f'{math.ceil(record.month_5)} (<span style="color: {"red" if record.mon_5_val_1 < 0 else "green"}">{record.mon_5_val_1}</span>/<span style="color: {"red" if record.mon_5_val_2 < 0 else "green"}">{record.mon_5_val_2}</span>)'
            record.mon_6 = f'{math.ceil(record.month_6)} (<span style="color: {"red" if record.mon_6_val_1 < 0 else "green"}">{record.mon_6_val_1}</span>/<span style="color: {"red" if record.mon_6_val_2 < 0 else "green"}">{record.mon_6_val_2}</span>)'
            record.mon_7 = f'{math.ceil(record.month_7)} (<span style="color: {"red" if record.mon_7_val_1 < 0 else "green"}">{record.mon_7_val_1}</span>/<span style="color: {"red" if record.mon_7_val_2 < 0 else "green"}">{record.mon_7_val_2}</span>)'
            record.mon_8 = f'{math.ceil(record.month_8)} (<span style="color: {"red" if record.mon_8_val_1 < 0 else "green"}">{record.mon_8_val_1}</span>/<span style="color: {"red" if record.mon_8_val_2 < 0 else "green"}">{record.mon_8_val_2}</span>)'
    
    def init(self):
        #This is a test
        # tools.drop_view_if_exists(self.env.cr, self._table)
        self._cr.execute("""
                         Drop view demand_model; 
                         
                         
                         CREATE VIEW demand_model AS
WITH inventory_on_order AS (
SELECT
pt.id AS product_id,
COALESCE(inventory.on_hand_quantity, 0) AS "In Inventory",
COALESCE(on_order.on_order_quantity, 0) AS "On Order"
FROM
product_product pp
JOIN product_template pt ON pp.product_tmpl_id = pt.id
LEFT JOIN (
SELECT
pt.id AS product_id,
SUM(sq.quantity) AS on_hand_quantity
FROM
stock_quant sq
JOIN stock_location sl ON sq.location_id = sl.id
JOIN product_product pp ON sq.product_id = pp.id
JOIN product_template pt ON pp.product_tmpl_id = pt.id
WHERE
sl.complete_name NOT LIKE 'Virtual Locations/%' -- Exclude virtual locations
AND sl.complete_name NOT LIKE 'Partners/%' -- Exclude partner locations
GROUP BY
pt.id
) inventory ON pp.id = inventory.product_id
LEFT JOIN (
SELECT
pt.id AS product_id,
pt.default_code AS product_code,
SUM(pol.product_qty - pol.qty_received) AS on_order_quantity
FROM
purchase_order_line pol
JOIN product_product pp ON pol.product_id = pp.id
JOIN product_template pt ON pp.product_tmpl_id = pt.id
JOIN purchase_order po ON pol.order_id = po.id
WHERE
po.state IN ('draft', 'sent', 'to approve', 'purchase', 'done') -- Include 'done' state
GROUP BY
pt.id
) on_order ON pt.id = on_order.product_id
),
component_mo_month AS (
SELECT
pt.id AS product_id,
pt.default_code AS product_code,
pt.name->>'en_US' AS product_name,
COALESCE(SUM(CASE WHEN TO_DATE(TO_CHAR(mo.date_start, 'YYYY-MM-DD'), 'YYYY-MM-DD') BETWEEN (DATE_TRUNC('month', CURRENT_DATE)::DATE) AND ((DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month' - INTERVAL '1 day')::DATE) THEN sm.product_uom_qty ELSE 0 END), 0) AS month_1,
COALESCE(SUM(CASE WHEN TO_DATE(TO_CHAR(mo.date_start, 'YYYY-MM-DD'), 'YYYY-MM-DD') BETWEEN ((DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month')::DATE) AND ((DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '2 months' - INTERVAL '1 day')::DATE) THEN sm.product_uom_qty ELSE 0 END), 0) AS month_2,
COALESCE(SUM(CASE WHEN TO_DATE(TO_CHAR(mo.date_start, 'YYYY-MM-DD'), 'YYYY-MM-DD') BETWEEN ((DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '2 months')::DATE) AND ((DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '3 months' - INTERVAL '1 day')::DATE) THEN sm.product_uom_qty ELSE 0 END), 0) AS month_3,
COALESCE(SUM(CASE WHEN TO_DATE(TO_CHAR(mo.date_start, 'YYYY-MM-DD'), 'YYYY-MM-DD') BETWEEN ((DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '3 months')::DATE) AND ((DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '4 months' - INTERVAL '1 day')::DATE) THEN sm.product_uom_qty ELSE 0 END), 0) AS month_4,
COALESCE(SUM(CASE WHEN TO_DATE(TO_CHAR(mo.date_start, 'YYYY-MM-DD'), 'YYYY-MM-DD') BETWEEN ((DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '4 months')::DATE) AND ((DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '5 months' - INTERVAL '1 day')::DATE) THEN sm.product_uom_qty ELSE 0 END), 0) AS month_5,
COALESCE(SUM(CASE WHEN TO_DATE(TO_CHAR(mo.date_start, 'YYYY-MM-DD'), 'YYYY-MM-DD') BETWEEN ((DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '5 months')::DATE) AND ((DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '6 months' - INTERVAL '1 day')::DATE) THEN sm.product_uom_qty ELSE 0 END), 0) AS month_6,
COALESCE(SUM(CASE WHEN TO_DATE(TO_CHAR(mo.date_start, 'YYYY-MM-DD'), 'YYYY-MM-DD') BETWEEN ((DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '6 months')::DATE) AND ((DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '7 months' - INTERVAL '1 day')::DATE) THEN sm.product_uom_qty ELSE 0 END), 0) AS month_7,
COALESCE(SUM(CASE WHEN TO_DATE(TO_CHAR(mo.date_start, 'YYYY-MM-DD'), 'YYYY-MM-DD') BETWEEN ((DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '7 months')::DATE) AND ((DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '8 months' - INTERVAL '1 day')::DATE) THEN sm.product_uom_qty ELSE 0 END), 0) AS month_8
FROM
mrp_production mo
JOIN stock_move sm ON mo.id = sm.raw_material_production_id
JOIN product_product p ON sm.product_id = p.id
JOIN product_template pt ON p.product_tmpl_id = pt.id
WHERE
mo.state = 'confirmed'
GROUP BY
pt.id,
pt.default_code,
pt.name
)
SELECT
row_number() OVER () AS id,
cmmv.product_id,
cmmv.product_code AS component_code,
cmmv.product_name AS component_name,
CASE WHEN pt.type = 'product' THEN false ELSE true END AS is_storable,
ioov."In Inventory" AS in_stock,
ioov."On Order" AS on_order,
CASE WHEN EXISTS (
SELECT 1
FROM mrp_bom mb
WHERE mb.product_tmpl_id = pt.id
) THEN true ELSE false END AS has_bom,
cmmv.month_1,
cmmv.month_2,
cmmv.month_3,
cmmv.month_4,
cmmv.month_5,
cmmv.month_6,
cmmv.month_7,
cmmv.month_8
FROM
component_mo_month cmmv
JOIN inventory_on_order ioov ON cmmv.product_id = ioov.product_id
JOIN product_product pp ON cmmv.product_id = pp.id
JOIN product_template pt ON pp.product_tmpl_id = pt.id; """ )  #random comment
        
        
        
        
        
        
# """
# CREATE VIEW component_inventory_mo_view AS
# WITH months AS (
# SELECT DISTINCT TO_DATE(mo_month, 'YYYY-MM') AS month
# FROM component_mo_view
# WHERE TO_DATE(mo_month, 'YYYY-MM') >= DATE_TRUNC('month', CURRENT_DATE)
# UNION
# SELECT GENERATE_SERIES(
# DATE_TRUNC('month', CURRENT_DATE)::DATE,
# DATE_TRUNC('month', CURRENT_DATE)::DATE + INTERVAL '7 months',
# INTERVAL '1 month'
# )
# )
# SELECT
# row_number() OVER () AS id,
# cmv.product_id,
# cmv.product_code AS component_code,
# cmv.product_name AS component_name,
# CASE WHEN pt.type = 'product' THEN false ELSE true END AS is_storable,
# ioov."In Inventory" AS in_stock,
# ioov."On Order" AS on_order,
# CASE WHEN EXISTS (
# SELECT 1
# FROM mrp_bom mb
# WHERE mb.product_tmpl_id = pt.id
# ) THEN true ELSE false END AS has_bom,
# SUM(CASE WHEN TO_DATE(cmv.mo_month, 'YYYY-MM') = m.month THEN cmv.component_quantity ELSE 0 END) AS month_1,
# SUM(CASE WHEN TO_DATE(cmv.mo_month, 'YYYY-MM') = m.month + INTERVAL '1 month' THEN cmv.component_quantity ELSE 0 END) AS month_2,
# SUM(CASE WHEN TO_DATE(cmv.mo_month, 'YYYY-MM') = m.month + INTERVAL '2 months' THEN cmv.component_quantity ELSE 0 END) AS month_3,
# SUM(CASE WHEN TO_DATE(cmv.mo_month, 'YYYY-MM') = m.month + INTERVAL '3 months' THEN cmv.component_quantity ELSE 0 END) AS month_4,
# SUM(CASE WHEN TO_DATE(cmv.mo_month, 'YYYY-MM') = m.month + INTERVAL '4 months' THEN cmv.component_quantity ELSE 0 END) AS month_5,
# SUM(CASE WHEN TO_DATE(cmv.mo_month, 'YYYY-MM') = m.month + INTERVAL '5 months' THEN cmv.component_quantity ELSE 0 END) AS month_6,
# SUM(CASE WHEN TO_DATE(cmv.mo_month, 'YYYY-MM') = m.month + INTERVAL '6 months' THEN cmv.component_quantity ELSE 0 END) AS month_7,
# SUM(CASE WHEN TO_DATE(cmv.mo_month, 'YYYY-MM') = m.month + INTERVAL '7 months' THEN cmv.component_quantity ELSE 0 END) AS month_8
# FROM
# component_mo_view cmv
# JOIN inventory_on_order_view ioov ON cmv.product_id = ioov.product_id
# JOIN product_product pp ON cmv.product_id = pp.id
# JOIN product_template pt ON pp.product_tmpl_id = pt.id
# LEFT JOIN months m ON TO_DATE(cmv.mo_month, 'YYYY-MM') <= m.month
# GROUP BY
# cmv.product_id,
# cmv.product_code,
# cmv.product_name,
# pt.type,
# ioov."In Inventory",
# ioov."On Order",
# CASE WHEN EXISTS (
# SELECT 1
# FROM mrp_bom mb
# WHERE mb.product_tmpl_id = pt.id
# ) THEN true ELSE false END;


# """