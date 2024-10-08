from odoo import models, fields, api, tools
import math
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class Demand(models.Model):
    _name = 'demand.model'
    _description = 'Demand Model'
    _rec_name = 'component_code'
    _auto = False
    _sql = True
    
    id = fields.Integer(string='ID', required=True, readonly=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, readonly=True)
    component_code = fields.Char(string='Component Code', required=False, readonly=True)
    component_name = fields.Char(string='Component Name', required=False, readonly=True)
    is_storable = fields.Boolean(string='Consumable?', required=False, readonly=True)
    has_bom = fields.Boolean(string='Has BOM?', required=False, readonly=True)
    in_stock = fields.Float(string='In Stock', required=False, readonly=True)
    on_order = fields.Float(string='On Order', required=False, readonly=True)
    current_month = fields.Date.today().month
    
    # Dynamic generation of month fields
    for i in range(1, 9):
        month_field = 'month_{}'.format(i)
        month_date = fields.Date.today() + relativedelta(months=i-1)
        month_name = month_date.strftime('%B %Y')
        vars()[month_field] = fields.Float(string=month_name, required=False, readonly=True, digits=(10, 2))
    
    # Update mon_1 to mon_8 fields with dynamic month names
    for i in range(1, 9):
        month_date = fields.Date.today() + relativedelta(months=i-1)
        month_name = month_date.strftime('%B %Y')
        vars()[f'mon_{i}_val_1'] = fields.Float(compute='_compute_values', string=f'{month_name} Value 1', store=False)
        vars()[f'mon_{i}_val_2'] = fields.Float(compute='_compute_values', string=f'{month_name} Value 2', store=False)
        vars()[f'mon_{i}'] = fields.Html(compute='_compute_values', string=month_name, store=False)
    
    component_link = fields.Html(string='Component Link', compute='_compute_component_code', readonly=True)

    def _compute_component_code(self):
        for record in self:
            product = record.product_id
            default_code = product.default_code or ''
            product_id = product.id
            
            button_code = '''
            <a href="/component_mo_view/{}" target="_blank"><i class="o_button_icon fa fa-fw fa-cogs me-1"></i><b>Manufacturing Orders <b></a>
            '''.format(product_id)
            
            record.component_link = button_code
    
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
        action = self.env.ref('edge_module.action_demand_purchase_orders').read()[0]
        action['domain'] = [('product_id', '=', self.product_id.id)] 
        action['context'] = {'search_default_product_id': self.product_id.id}
        return action

    @api.depends('in_stock', 'on_order')
    def _compute_values(self):
        for record in self:
            for i in range(1, 9):
                month_sum = sum(getattr(record, f'month_{j}') for j in range(1, i+1))
                setattr(record, f'mon_{i}_val_1', math.ceil(record.in_stock - month_sum))
                setattr(record, f'mon_{i}_val_2', math.ceil(record.in_stock + record.on_order - month_sum))
                
                month_value = getattr(record, f'month_{i}')
                val_1 = getattr(record, f'mon_{i}_val_1')
                val_2 = getattr(record, f'mon_{i}_val_2')
                
                setattr(record, f'mon_{i}', f'{math.ceil(month_value)} (<span style="color: {"red" if val_1 < 0 else "green"}">{val_1}</span>/<span style="color: {"red" if val_2 < 0 else "green"}">{val_2}</span>)')


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
    product_template pt
    LEFT JOIN (
        SELECT
            pp.product_tmpl_id,
            SUM(
                CASE
                    WHEN sl_src.usage != 'internal' AND sl_dest.usage = 'internal' THEN sm.product_qty
                    WHEN sl_src.usage = 'internal' AND sl_dest.usage != 'internal' THEN -sm.product_qty
                    ELSE 0
                END
            ) AS on_hand_quantity
        FROM
            stock_move sm
            JOIN stock_location sl_src ON sm.location_id = sl_src.id
            JOIN stock_location sl_dest ON sm.location_dest_id = sl_dest.id
            JOIN product_product pp ON sm.product_id = pp.id
        WHERE
            sm.state = 'done'
        GROUP BY
            pp.product_tmpl_id
    ) inventory ON pt.id = inventory.product_tmpl_id
    LEFT JOIN (
        SELECT
            pt.id,
            SUM(pol.product_qty - pol.qty_received) AS on_order_quantity
        FROM
            purchase_order_line pol
            JOIN product_product pp ON pol.product_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            JOIN purchase_order po ON pol.order_id = po.id
        WHERE
            po.state IN ('draft', 'sent', 'to approve', 'purchase', 'done')
        GROUP BY
            pt.id
    ) on_order ON pt.id = on_order.id),
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
mo.state = 'confirmed' or mo.state = 'progress'
GROUP BY
pt.id,
pt.default_code,
pt.name
)
SELECT
cmmv.product_id as id,
pp.id AS product_id,
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
JOIN product_template pt ON cmmv.product_id = pt.id
JOIN product_product pp ON pp.product_tmpl_id = pt.id
; """ )  #random comment
        
        
        
        
        
        
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