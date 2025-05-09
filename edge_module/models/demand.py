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
    min_lead_time = fields.Integer(string='Minimum Lead Time', required=False, readonly=True)
    order_by_date_value = fields.Date(string='Order By Date', compute='_compute_order_by_date', store=False, readonly=True)
    order_by_display = fields.Html(string='Order By', compute='_compute_order_by_display', store=False)
    vendor_stocked_consumable = fields.Boolean(related='product_id.vendor_stocked_consumable', string='Vendor Stocked Consumable', readonly=True)
    # buyer_id = fields.Many2one('res.users', string='Buyer', readonly=True)

    def _get_first_negative_month(self):
        """Helper method to find the first month where demand goes negative"""
        for i in range(1, 9):
            demand_sum = sum(getattr(self, f'month_{j}') for j in range(1, i+1))
            supply_sum = sum(getattr(self, f'mon_{j}_val_1') for j in range(1, i+1))
            if (self.in_stock + supply_sum - demand_sum) < 0:
                return i
        return None

    @api.depends('in_stock', 'on_order', 'min_lead_time')
    def _compute_order_by_date(self):
        for record in self:
            negative_month = record._get_first_negative_month()
            if negative_month:
                current_date = fields.Date.today()
                negative_date = current_date + relativedelta(months=negative_month-1, day=1)
                record.order_by_date_value = negative_date - relativedelta(days=record.min_lead_time or 0)
            else:
                record.order_by_date_value = False

    @api.depends('order_by_date_value')
    def _compute_order_by_display(self):
        for record in self:
            if record.order_by_date_value:
                days_until = (record.order_by_date_value - fields.Date.today()).days
                badge_class = 'bg-danger' if days_until < 0 else 'bg-warning' if days_until < 14 else 'bg-info'
                badge_text = 'Late' if days_until < 0 else 'Warning' if days_until < 14 else 'OK'
                date_str = record.order_by_date_value.strftime('%b %d')
                record.order_by_display = f'''
                    <div class="d-flex align-items-center">
                        <span class="badge rounded-pill text-{badge_class}">{date_str}</span>
                    </div>
                '''
            else:
                record.order_by_display = '''
                    <div class="d-flex align-items-center">
                        <span class="badge rounded-pill text-bg-success">No Shortage</span>
                    </div>
                '''
    
    @api.depends('product_id', 'component_code')
    def _compute_product_link_code(self):
        for record in self:
            if record.product_id and record.component_code:
                record.product_link_code = f'''
                    <a href="/web#id={record.product_id.id}&model=product.product&view_type=form">
                        {record.component_code}
                    </a>
                '''
            else:
                record.product_link_code = record.component_code or ''

    product_link_code = fields.Html(string='Product', compute='_compute_product_link_code', readonly=True)
    
    
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
        vars()[f'mon_{i}_val_1'] = fields.Float(compute='_compute_values', string=f'{month_name} Supply', store=False)
        vars()[f'mon_{i}_val_2'] = fields.Float(compute='_compute_values', string=f'{month_name} Demand', store=False)
        vars()[f'mon_{i}'] = fields.Html(compute='_compute_values', string=month_name, store=False, help='Demand / Supply / Delta')
    
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


    """
    Retrieve a detailed schedule of purchase orders for each product by returning a dictionary mapping each product's supply quantities over the next eight months
    """
    def _get_purchase_order_supply_schedule(self):
        self.ensure_one()
        product = self.product_id

        # Search for relevant purchase order lines
        purchase_orders = self.env['purchase.order.line'].search([
            ('product_id', '=', product.id),
            ('order_id.state', 'in', ['purchase', 'done', 'sent', 'to approve']),
        ])

        # Filter orders where qty_received < product_qty
        purchase_orders = purchase_orders.filtered(lambda po: po.product_qty > 0 and po.qty_received < po.product_qty)

        # Prepare supply schedule
        supply_schedule = {i: 0 for i in range(1, 9)}
        for order in purchase_orders:
            order_date = order.order_id.date_planned
            order_month = order_date.month
            order_year = order_date.year
            order_quantity = order.product_qty - order.qty_received
            order_month_index = (order_year - fields.Date.today().year) * 12 + order_month - fields.Date.today().month + 1
            if order_month_index in supply_schedule:
                supply_schedule[order_month_index] += order_quantity
        return supply_schedule


    """
    calculate and sets demand, supply, and delta values for each month
    """
    @api.depends('in_stock', 'on_order')
    def _compute_values(self):
        for record in self:
            supply_schedule = record._get_purchase_order_supply_schedule()
            cumulative_supply = 0
            cumulative_demand = 0
            
            for i in range(1, 9):
                month_supply = supply_schedule.get(i, 0)
                month_demand = getattr(record, f'month_{i}')
                
                cumulative_supply += month_supply
                cumulative_demand += month_demand
                
                # Calculate month delta
                month_delta = record.in_stock + cumulative_supply - cumulative_demand
                
                setattr(record, f'mon_{i}_val_1', month_supply)
                setattr(record, f'mon_{i}_val_2', month_demand)
                
                # Style HTML based on delta value with a full explanation
                if month_delta < 0:
                    delta_html = f'<span class="text-danger">{round(month_delta)}</span>'
                else:
                    delta_html = f'<span class="text-success">{round(month_delta)}</span>'

                # Full cell with tooltip
                full_html = f'<span title="Demand / Supply / Delta">{round(month_demand)} / {round(month_supply)} / {delta_html}</span>'
                
                setattr(record, f'mon_{i}', full_html)
                




    def init(self):
        #This is a test
        # tools.drop_view_if_exists(self.env.cr, self._table)
        self._cr.execute("""
                         Drop view demand_model; 
                         
                         
                         CREATE VIEW demand_model AS
  WITH inventory AS (
    SELECT pt_1.id AS product_id,
        COALESCE(sum(
            CASE
                WHEN ((sl.usage)::text = 'internal'::text) THEN sq.quantity
                ELSE (0)::numeric
            END), (0)::numeric) AS "In Inventory"
    FROM (((product_template pt_1
        LEFT JOIN product_product pp_1 ON ((pp_1.product_tmpl_id = pt_1.id)))
        LEFT JOIN stock_quant sq ON ((sq.product_id = pp_1.id)))
        LEFT JOIN stock_location sl ON ((sq.location_id = sl.id)))
    GROUP BY pt_1.id
),
purchase_orders AS (
    SELECT pt_1.id AS product_id,
        COALESCE(sum((pol.product_qty - pol.qty_received)) FILTER (WHERE (((po_1.state)::text = ANY (ARRAY[('sent'::character varying)::text, ('to approve'::character varying)::text, ('purchase'::character varying)::text, ('done'::character varying)::text])) AND (pol.product_qty > pol.qty_received) AND ((po_1.state)::text <> 'cancel'::text))), (0)::numeric) AS "On Order"
    FROM (((product_template pt_1
        LEFT JOIN product_product pp_1 ON ((pp_1.product_tmpl_id = pt_1.id)))
        LEFT JOIN purchase_order_line pol ON ((pol.product_id = pp_1.id)))
        LEFT JOIN purchase_order po_1 ON ((pol.order_id = po_1.id)))
    GROUP BY pt_1.id
),
component_mo_month AS (
    SELECT pt_1.id AS product_id,
        pt_1.default_code AS product_code,
        (pt_1.name ->> 'en_US'::text) AS product_name,
        COALESCE(sum(
            CASE
                WHEN ((to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) >= (date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone))::date) AND (to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) <= (((date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone) + '1 mon'::interval) - '1 day'::interval))::date)) THEN sm.product_uom_qty
                ELSE (0)::numeric
            END), (0)::numeric) AS month_1,
        COALESCE(sum(
            CASE
                WHEN ((to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) >= ((date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone) + '1 mon'::interval))::date) AND (to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) <= (((date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone) + '2 mons'::interval) - '1 day'::interval))::date)) THEN sm.product_uom_qty
                ELSE (0)::numeric
            END), (0)::numeric) AS month_2,
        COALESCE(sum(
            CASE
                WHEN ((to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) >= ((date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone) + '2 mons'::interval))::date) AND (to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) <= (((date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone) + '3 mons'::interval) - '1 day'::interval))::date)) THEN sm.product_uom_qty
                ELSE (0)::numeric
            END), (0)::numeric) AS month_3,
        COALESCE(sum(
            CASE
                WHEN ((to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) >= ((date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone) + '3 mons'::interval))::date) AND (to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) <= (((date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone) + '4 mons'::interval) - '1 day'::interval))::date)) THEN sm.product_uom_qty
                ELSE (0)::numeric
            END), (0)::numeric) AS month_4,
        COALESCE(sum(
            CASE
                WHEN ((to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) >= ((date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone) + '4 mons'::interval))::date) AND (to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) <= (((date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone) + '5 mons'::interval) - '1 day'::interval))::date)) THEN sm.product_uom_qty
                ELSE (0)::numeric
            END), (0)::numeric) AS month_5,
        COALESCE(sum(
            CASE
                WHEN ((to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) >= ((date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone) + '5 mons'::interval))::date) AND (to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) <= (((date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone) + '6 mons'::interval) - '1 day'::interval))::date)) THEN sm.product_uom_qty
                ELSE (0)::numeric
            END), (0)::numeric) AS month_6,
        COALESCE(sum(
            CASE
                WHEN ((to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) >= ((date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone) + '6 mons'::interval))::date) AND (to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) <= (((date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone) + '7 mons'::interval) - '1 day'::interval))::date)) THEN sm.product_uom_qty
                ELSE (0)::numeric
            END), (0)::numeric) AS month_7,
        COALESCE(sum(
            CASE
                WHEN ((to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) >= ((date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone) + '7 mons'::interval))::date) AND (to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) <= (((date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone) + '8 mons'::interval) - '1 day'::interval))::date)) THEN sm.product_uom_qty
                ELSE (0)::numeric
            END), (0)::numeric) AS month_8
    FROM (((mrp_production mo
        JOIN stock_move sm ON ((mo.id = sm.raw_material_production_id)))
        JOIN product_product p ON ((sm.product_id = p.id)))
        JOIN product_template pt_1 ON ((p.product_tmpl_id = pt_1.id)))
    WHERE (((mo.state)::text = 'confirmed'::text) OR ((mo.state)::text = 'progress'::text))
    GROUP BY pt_1.id, pt_1.default_code, pt_1.name
),
lead_times AS (
    SELECT 
        pt.id as product_id,
        MIN(COALESCE(si.delay, 0)) as min_lead_time
    FROM 
        product_template pt
    LEFT JOIN 
        product_supplierinfo si ON si.product_tmpl_id = pt.id
    GROUP BY 
        pt.id
)
SELECT 
    cmmv.product_id AS id,
    pp.id AS product_id,
    cmmv.product_code AS component_code,
    cmmv.product_name AS component_name,
    CASE
        WHEN ((pt.type)::text = 'product'::text) THEN false
        ELSE true
    END AS is_storable,
    i."In Inventory" AS in_stock,
    po."On Order" AS on_order,
    CASE
        WHEN (EXISTS ( SELECT 1
            FROM mrp_bom mb
            WHERE (mb.product_tmpl_id = pt.id))) THEN true
        ELSE false
    END AS has_bom,
    lt.min_lead_time,
    cmmv.month_1,
    cmmv.month_2,
    cmmv.month_3,
    cmmv.month_4,
    cmmv.month_5,
    cmmv.month_6,
    cmmv.month_7,
    cmmv.month_8
FROM ((((component_mo_month cmmv
    JOIN product_template pt ON ((cmmv.product_id = pt.id)))
    JOIN product_product pp ON ((pp.product_tmpl_id = pt.id)))
    LEFT JOIN inventory i ON ((i.product_id = cmmv.product_id)))
    LEFT JOIN purchase_orders po ON ((po.product_id = cmmv.product_id)))
    LEFT JOIN lead_times lt ON ((lt.product_id = cmmv.product_id));
     """ )  #random comment
        
        
        
        
        
        
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