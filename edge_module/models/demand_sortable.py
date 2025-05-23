from odoo import models, fields, api, tools
from datetime import datetime # Keep this
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class SortableDemand(models.Model):
    _name = 'sortable.demand.model'
    _description = 'Sortable Demand Model'
    _rec_name = 'component_code'
    _auto = False
    _sql = True # Keep this to indicate it's based on the SQL view above
    
    # Fields directly from SQL view (or renamed for clarity)
    id = fields.Integer(string='ID', required=True, readonly=True) # Corresponds to product_template.id
    product_id = fields.Many2one('product.product', string='Product', readonly=True) # Corresponds to product.product.id
    component_code = fields.Char(string='Component Code', readonly=True)
    component_name = fields.Char(string='Component Name', readonly=True)
    is_storable = fields.Boolean(string='Consumable?', readonly=True)
    has_bom = fields.Boolean(string='Has BOM?', readonly=True)
    in_stock = fields.Float(string='In Stock', readonly=True)
    on_order = fields.Float(string='On Order', readonly=True)
    min_lead_time = fields.Integer(string='Minimum Lead Time', readonly=True)
    
    # This field is now directly from the SQL view
    order_by_date_value = fields.Date(string='Order By Date Value', readonly=True)

    # HTML display for Order By Date, computed based on the SQL field
    order_by_display = fields.Html(string='Order By', compute='_compute_order_by_display', store=False)

    vendor_stocked_consumable = fields.Boolean(related='product_id.vendor_stocked_consumable', string='Vendor Stocked Consumable', readonly=True)
    product_link_code = fields.Html(string='Product', compute='_compute_product_link_code', readonly=True)
    component_link = fields.Html(string='Component Link', compute='_compute_component_code', readonly=True)

    # REMOVE: _get_first_negative_month, _compute_order_by_date (Python version)
    # REMOVE: _get_purchase_order_supply_schedule, _compute_values

    @api.depends('order_by_date_value') # Now depends on the SQL-calculated field
    def _compute_order_by_display(self):
        for record in self:
            if record.order_by_date_value:
                days_until = (record.order_by_date_value - fields.Date.today()).days
                # Determine badge class and text based on days_until
                if days_until < 0:
                    badge_class = 'bg-danger'
                    badge_text = 'Late'
                elif days_until < 14: # Example: 2 weeks warning
                    badge_class = 'bg-warning text-dark' # Ensure text is visible on warning
                    badge_text = 'Warning'
                else:
                    badge_class = 'bg-info text-dark' # Ensure text is visible on info
                    badge_text = 'OK'
                
                date_str = record.order_by_date_value.strftime('%b %d')
                record.order_by_display = f'''
                    <div class="d-flex align-items-center">
                        <span class="badge rounded-pill {badge_class}">{date_str} ({badge_text})</span>
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
                    <a href="/web#id={record.product_id.id}&model=product.product&view_type=form" target="_blank">
                        {record.component_code}
                    </a>
                '''
            else:
                record.product_link_code = record.component_code or ''

    def _compute_component_code(self):
        for record in self:
            if not record.product_id: # product_id here refers to product.product
                record.component_link = ''
                continue
            product_template_id = record.product_id.product_tmpl_id.id # Get template ID from product.product
            
            button_code = '''
            <a href="/component_mo_view/{}" target="_blank"><i class="o_button_icon fa fa-fw fa-cogs me-1"></i><b>Manufacturing Orders</b></a>
            '''.format(product_template_id) # Use template_id if your /component_mo_view expects it
            
            record.component_link = button_code
            
    # Helper function to create compute methods for monthly HTML display
    def _create_monthly_display_compute(month_idx):
        # These field names must match SQL view aliases or model field names
        demand_field_name = f'month_{month_idx}'     # e.g., month_1 (demand from SQL)
        supply_field_name = f'supply_m{month_idx}'   # e.g., supply_m1 (supply from SQL)
        balance_field_name = f'balance_m{month_idx}' # e.g., balance_m1 (balance from SQL)

        @api.depends(demand_field_name, supply_field_name, balance_field_name)
        def _compute_display(self):
            for record in self:
                demand = getattr(record, demand_field_name, 0.0) or 0.0
                supply = getattr(record, supply_field_name, 0.0) or 0.0
                balance = getattr(record, balance_field_name, 0.0) or 0.0
                
                delta_html = f'<span class="text-danger">{round(balance)}</span>' if balance < 0 else f'<span class="text-success">{round(balance)}</span>'
                # Tooltip explains: Demand / Supply / Projected On Hand
                full_html = f'<span title="Demand: {round(demand)} / Supply: {round(supply)} / Projected On Hand: {round(balance)}">{round(demand)} / {round(supply)} / {delta_html}</span>'
                setattr(record, f'mon_{month_idx}', full_html) # Sets mon_1, mon_2, etc.
        return _compute_display

    # Dynamic generation of month-related fields
    for i in range(1, 9):
        month_date = fields.Date.today() + relativedelta(months=i-1)
        month_name_full = month_date.strftime('%B %Y') # e.g., "May 2025"
        # Shorter name for column headers in the tree view
        month_header_name = month_date.strftime('%B') if (month_date.year == fields.Date.today().year) else month_date.strftime('%b %y')

        # Demand fields (month_1, month_2, ... from SQL alias demand_mX)
        # Their string can be the full month name for clarity if shown directly
        vars()[f'month_{i}'] = fields.Float(string=month_name_full, readonly=True, digits=(10, 2))

        # Supply fields (supply_m1, supply_m2, ... from SQL alias supply_mX)
        vars()[f'supply_m{i}'] = fields.Float(string=f'{month_header_name} Supply Value', readonly=True)
        
        # Balance fields (balance_m1, balance_m2, ... from SQL alias balance_mX)
        vars()[f'balance_m{i}'] = fields.Float(string=f'{month_header_name} Balance Value', readonly=True)
        
        # HTML display fields (mon_1, mon_2, ...)
        # These use the shorter month_header_name for their column title
        vars()[f'mon_{i}'] = fields.Html(
            compute=_create_monthly_display_compute(i),
            string=month_header_name, 
            store=False # Remains store=False as it's a display field
        )

    def open_mo_list(self):
        # This method seems to be unused in the provided XML, but ensure product_id is correct if used.
        # Assuming self.id is product_template.id and you need product.product for the URL.
        # If /mo_list/ expects product.template.id, then self.id is fine.
        # If it expects product.product.id, you'd use self.product_id.id.
        self.ensure_one()
        # product_id_for_url = self.product_id.id # if MO list is by product.product
        product_id_for_url = self.id # if MO list is by product.template (as self.id is template id)
        return {
            'type': 'ir.actions.act_url',
            'url': '/mo_list/%s' % product_id_for_url,
            'target': 'new',
        }

    def action_view_purchase_orders(self):
        self.ensure_one()
        # Ensure self.product_id is the product.product record
        if not self.product_id:
            return {} # Or raise a warning
        action = self.env['ir.actions.act_window']._for_xml_id('edge_module.action_sortable_demand_purchase_orders') # Updated action reference
        action['domain'] = [('product_id', '=', self.product_id.id)] 
        action['context'] = {'search_default_product_id': self.product_id.id, 'default_product_id': self.product_id.id}
        return action

    # init method is defined above with the new SQL

    def init(self):
            tools.drop_view_if_exists(self.env.cr, self._table) # Use IF EXISTS
            self._cr.execute("""
                CREATE OR REPLACE VIEW sortable_demand_model AS
                WITH inventory AS (
                    SELECT pt_1.id AS product_tmpl_id, -- Changed to product_tmpl_id for clarity
                        COALESCE(sum(
                            CASE
                                WHEN ((sl.usage)::text = 'internal'::text) THEN sq.quantity
                                ELSE (0)::numeric
                            END), (0)::numeric) AS "In Inventory"
                    FROM product_template pt_1
                    LEFT JOIN product_product pp_1 ON pp_1.product_tmpl_id = pt_1.id
                    LEFT JOIN stock_quant sq ON sq.product_id = pp_1.id
                    LEFT JOIN stock_location sl ON sq.location_id = sl.id
                    GROUP BY pt_1.id
                ),
                purchase_orders_total AS ( -- Renamed for clarity, this is the total "On Order"
                    SELECT pt_1.id AS product_tmpl_id,
                        COALESCE(sum((pol.product_qty - pol.qty_received)) FILTER (WHERE (((po_1.state)::text = ANY (ARRAY[('sent'::character varying)::text, ('to approve'::character varying)::text, ('purchase'::character varying)::text, ('done'::character varying)::text])) AND (pol.product_qty > pol.qty_received) AND ((po_1.state)::text <> 'cancel'::text))), (0)::numeric) AS "On Order"
                    FROM product_template pt_1
                    LEFT JOIN product_product pp_1 ON pp_1.product_tmpl_id = pt_1.id
                    LEFT JOIN purchase_order_line pol ON pol.product_id = pp_1.id
                    LEFT JOIN purchase_order po_1 ON pol.order_id = po_1.id
                    GROUP BY pt_1.id
                ),
                component_mo_month AS ( -- This is demand per month
                    SELECT pt_1.id AS product_tmpl_id,
                        pt_1.default_code AS product_code,
                        (pt_1.name ->> 'en_US'::text) AS product_name,
                        COALESCE(sum(CASE WHEN ((to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) >= (date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone))::date) AND (to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) <= (((date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone) + '1 mon'::interval) - '1 day'::interval))::date)) THEN sm.product_uom_qty ELSE (0)::numeric END), (0)::numeric) AS demand_m1,
                        COALESCE(sum(CASE WHEN ((to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) >= ((date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone) + '1 mon'::interval))::date) AND (to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) <= (((date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone) + '2 mons'::interval) - '1 day'::interval))::date)) THEN sm.product_uom_qty ELSE (0)::numeric END), (0)::numeric) AS demand_m2,
                        COALESCE(sum(CASE WHEN ((to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) >= ((date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone) + '2 mons'::interval))::date) AND (to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) <= (((date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone) + '3 mons'::interval) - '1 day'::interval))::date)) THEN sm.product_uom_qty ELSE (0)::numeric END), (0)::numeric) AS demand_m3,
                        COALESCE(sum(CASE WHEN ((to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) >= ((date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone) + '3 mons'::interval))::date) AND (to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) <= (((date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone) + '4 mons'::interval) - '1 day'::interval))::date)) THEN sm.product_uom_qty ELSE (0)::numeric END), (0)::numeric) AS demand_m4,
                        COALESCE(sum(CASE WHEN ((to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) >= ((date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone) + '4 mons'::interval))::date) AND (to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) <= (((date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone) + '5 mons'::interval) - '1 day'::interval))::date)) THEN sm.product_uom_qty ELSE (0)::numeric END), (0)::numeric) AS demand_m5,
                        COALESCE(sum(CASE WHEN ((to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) >= ((date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone) + '5 mons'::interval))::date) AND (to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) <= (((date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone) + '6 mons'::interval) - '1 day'::interval))::date)) THEN sm.product_uom_qty ELSE (0)::numeric END), (0)::numeric) AS demand_m6,
                        COALESCE(sum(CASE WHEN ((to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) >= ((date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone) + '6 mons'::interval))::date) AND (to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) <= (((date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone) + '7 mons'::interval) - '1 day'::interval))::date)) THEN sm.product_uom_qty ELSE (0)::numeric END), (0)::numeric) AS demand_m7,
                        COALESCE(sum(CASE WHEN ((to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) >= ((date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone) + '7 mons'::interval))::date) AND (to_date(to_char(mo.date_start, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text) <= (((date_trunc('month'::text, (CURRENT_DATE)::timestamp with time zone) + '8 mons'::interval) - '1 day'::interval))::date)) THEN sm.product_uom_qty ELSE (0)::numeric END), (0)::numeric) AS demand_m8
                    FROM mrp_production mo
                    JOIN stock_move sm ON mo.id = sm.raw_material_production_id
                    JOIN product_product p ON sm.product_id = p.id
                    JOIN product_template pt_1 ON p.product_tmpl_id = pt_1.id
                    WHERE ((mo.state)::text = 'confirmed'::text) OR ((mo.state)::text = 'progress'::text)
                    GROUP BY pt_1.id, pt_1.default_code, pt_1.name
                ),
                lead_times AS (
                    SELECT pt.id as product_tmpl_id, MIN(COALESCE(si.delay, 0)) as min_lead_time
                    FROM product_template pt
                    LEFT JOIN product_supplierinfo si ON si.product_tmpl_id = pt.id
                    GROUP BY pt.id
                ),
                po_supply_monthly AS ( -- Supply per month from purchase orders
                    SELECT
                        pp.product_tmpl_id,
                        COALESCE(SUM(pol.product_qty - pol.qty_received) FILTER (WHERE po.date_planned >= date_trunc('month', CURRENT_DATE) AND po.date_planned < (date_trunc('month', CURRENT_DATE) + INTERVAL '1 month')), 0) AS supply_m1,
                        COALESCE(SUM(pol.product_qty - pol.qty_received) FILTER (WHERE po.date_planned >= (date_trunc('month', CURRENT_DATE) + INTERVAL '1 month') AND po.date_planned < (date_trunc('month', CURRENT_DATE) + INTERVAL '2 months')), 0) AS supply_m2,
                        COALESCE(SUM(pol.product_qty - pol.qty_received) FILTER (WHERE po.date_planned >= (date_trunc('month', CURRENT_DATE) + INTERVAL '2 months') AND po.date_planned < (date_trunc('month', CURRENT_DATE) + INTERVAL '3 months')), 0) AS supply_m3,
                        COALESCE(SUM(pol.product_qty - pol.qty_received) FILTER (WHERE po.date_planned >= (date_trunc('month', CURRENT_DATE) + INTERVAL '3 months') AND po.date_planned < (date_trunc('month', CURRENT_DATE) + INTERVAL '4 months')), 0) AS supply_m4,
                        COALESCE(SUM(pol.product_qty - pol.qty_received) FILTER (WHERE po.date_planned >= (date_trunc('month', CURRENT_DATE) + INTERVAL '4 months') AND po.date_planned < (date_trunc('month', CURRENT_DATE) + INTERVAL '5 months')), 0) AS supply_m5,
                        COALESCE(SUM(pol.product_qty - pol.qty_received) FILTER (WHERE po.date_planned >= (date_trunc('month', CURRENT_DATE) + INTERVAL '5 months') AND po.date_planned < (date_trunc('month', CURRENT_DATE) + INTERVAL '6 months')), 0) AS supply_m6,
                        COALESCE(SUM(pol.product_qty - pol.qty_received) FILTER (WHERE po.date_planned >= (date_trunc('month', CURRENT_DATE) + INTERVAL '6 months') AND po.date_planned < (date_trunc('month', CURRENT_DATE) + INTERVAL '7 months')), 0) AS supply_m7,
                        COALESCE(SUM(pol.product_qty - pol.qty_received) FILTER (WHERE po.date_planned >= (date_trunc('month', CURRENT_DATE) + INTERVAL '7 months') AND po.date_planned < (date_trunc('month', CURRENT_DATE) + INTERVAL '8 months')), 0) AS supply_m8
                    FROM purchase_order_line pol
                    JOIN purchase_order po ON pol.order_id = po.id
                    JOIN product_product pp ON pol.product_id = pp.id
                    WHERE po.state IN ('purchase', 'done', 'sent', 'to approve') AND pol.product_qty > pol.qty_received
                    AND po.date_planned >= date_trunc('month', CURRENT_DATE)
                    AND po.date_planned < (date_trunc('month', CURRENT_DATE) + INTERVAL '8 months')
                    GROUP BY pp.product_tmpl_id
                ),
                calculated_figures AS (
                    SELECT
                        cmmv.product_tmpl_id,
                        cmmv.product_code,
                        cmmv.product_name,
                        COALESCE(i."In Inventory", 0) AS in_stock_val,
                        COALESCE(lt.min_lead_time, 0) AS min_lead_time_val,
                        
                        COALESCE(cmmv.demand_m1, 0) AS demand_m1, COALESCE(posm.supply_m1, 0) AS supply_m1,
                        (COALESCE(i."In Inventory", 0) + COALESCE(posm.supply_m1, 0) - COALESCE(cmmv.demand_m1, 0)) AS balance_m1,
                        
                        COALESCE(cmmv.demand_m2, 0) AS demand_m2, COALESCE(posm.supply_m2, 0) AS supply_m2,
                        (COALESCE(i."In Inventory", 0) + COALESCE(posm.supply_m1, 0) + COALESCE(posm.supply_m2, 0) - COALESCE(cmmv.demand_m1, 0) - COALESCE(cmmv.demand_m2, 0)) AS balance_m2,

                        COALESCE(cmmv.demand_m3, 0) AS demand_m3, COALESCE(posm.supply_m3, 0) AS supply_m3,
                        (COALESCE(i."In Inventory", 0) + COALESCE(posm.supply_m1, 0) + COALESCE(posm.supply_m2, 0) + COALESCE(posm.supply_m3, 0) - COALESCE(cmmv.demand_m1, 0) - COALESCE(cmmv.demand_m2, 0) - COALESCE(cmmv.demand_m3, 0)) AS balance_m3,

                        COALESCE(cmmv.demand_m4, 0) AS demand_m4, COALESCE(posm.supply_m4, 0) AS supply_m4,
                        (COALESCE(i."In Inventory", 0) + COALESCE(posm.supply_m1, 0) + COALESCE(posm.supply_m2, 0) + COALESCE(posm.supply_m3, 0) + COALESCE(posm.supply_m4, 0) - COALESCE(cmmv.demand_m1, 0) - COALESCE(cmmv.demand_m2, 0) - COALESCE(cmmv.demand_m3, 0) - COALESCE(cmmv.demand_m4, 0)) AS balance_m4,

                        COALESCE(cmmv.demand_m5, 0) AS demand_m5, COALESCE(posm.supply_m5, 0) AS supply_m5,
                        (COALESCE(i."In Inventory", 0) + COALESCE(posm.supply_m1, 0) + COALESCE(posm.supply_m2, 0) + COALESCE(posm.supply_m3, 0) + COALESCE(posm.supply_m4, 0) + COALESCE(posm.supply_m5, 0) - COALESCE(cmmv.demand_m1, 0) - COALESCE(cmmv.demand_m2, 0) - COALESCE(cmmv.demand_m3, 0) - COALESCE(cmmv.demand_m4, 0) - COALESCE(cmmv.demand_m5, 0)) AS balance_m5,

                        COALESCE(cmmv.demand_m6, 0) AS demand_m6, COALESCE(posm.supply_m6, 0) AS supply_m6,
                        (COALESCE(i."In Inventory", 0) + COALESCE(posm.supply_m1, 0) + COALESCE(posm.supply_m2, 0) + COALESCE(posm.supply_m3, 0) + COALESCE(posm.supply_m4, 0) + COALESCE(posm.supply_m5, 0) + COALESCE(posm.supply_m6, 0) - COALESCE(cmmv.demand_m1, 0) - COALESCE(cmmv.demand_m2, 0) - COALESCE(cmmv.demand_m3, 0) - COALESCE(cmmv.demand_m4, 0) - COALESCE(cmmv.demand_m5, 0) - COALESCE(cmmv.demand_m6, 0)) AS balance_m6,

                        COALESCE(cmmv.demand_m7, 0) AS demand_m7, COALESCE(posm.supply_m7, 0) AS supply_m7,
                        (COALESCE(i."In Inventory", 0) + COALESCE(posm.supply_m1, 0) + COALESCE(posm.supply_m2, 0) + COALESCE(posm.supply_m3, 0) + COALESCE(posm.supply_m4, 0) + COALESCE(posm.supply_m5, 0) + COALESCE(posm.supply_m6, 0) + COALESCE(posm.supply_m7, 0) - COALESCE(cmmv.demand_m1, 0) - COALESCE(cmmv.demand_m2, 0) - COALESCE(cmmv.demand_m3, 0) - COALESCE(cmmv.demand_m4, 0) - COALESCE(cmmv.demand_m5, 0) - COALESCE(cmmv.demand_m6, 0) - COALESCE(cmmv.demand_m7, 0)) AS balance_m7,

                        COALESCE(cmmv.demand_m8, 0) AS demand_m8, COALESCE(posm.supply_m8, 0) AS supply_m8,
                        (COALESCE(i."In Inventory", 0) + COALESCE(posm.supply_m1, 0) + COALESCE(posm.supply_m2, 0) + COALESCE(posm.supply_m3, 0) + COALESCE(posm.supply_m4, 0) + COALESCE(posm.supply_m5, 0) + COALESCE(posm.supply_m6, 0) + COALESCE(posm.supply_m7, 0) + COALESCE(posm.supply_m8, 0) - COALESCE(cmmv.demand_m1, 0) - COALESCE(cmmv.demand_m2, 0) - COALESCE(cmmv.demand_m3, 0) - COALESCE(cmmv.demand_m4, 0) - COALESCE(cmmv.demand_m5, 0) - COALESCE(cmmv.demand_m6, 0) - COALESCE(cmmv.demand_m7, 0) - COALESCE(cmmv.demand_m8, 0)) AS balance_m8
                    FROM component_mo_month cmmv
                    LEFT JOIN inventory i ON i.product_tmpl_id = cmmv.product_tmpl_id
                    LEFT JOIN po_supply_monthly posm ON posm.product_tmpl_id = cmmv.product_tmpl_id
                    LEFT JOIN lead_times lt ON lt.product_tmpl_id = cmmv.product_tmpl_id
                )
                SELECT
                    cf.product_tmpl_id AS id, -- This is product_template.id
                    pp.id AS product_id, -- This is product.product.id
                    cf.product_code AS component_code,
                    cf.product_name AS component_name,
                    CASE WHEN pt.type = 'product' THEN false ELSE true END AS is_storable,
                    cf.in_stock_val AS in_stock,
                    pot."On Order" AS on_order,
                    (EXISTS (SELECT 1 FROM mrp_bom mb WHERE mb.product_tmpl_id = pt.id)) AS has_bom,
                    cf.min_lead_time_val AS min_lead_time,

                    cf.demand_m1 AS month_1, cf.demand_m2 AS month_2, cf.demand_m3 AS month_3, cf.demand_m4 AS month_4, cf.demand_m5 AS month_5, cf.demand_m6 AS month_6, cf.demand_m7 AS month_7, cf.demand_m8 AS month_8, -- Demand fields
                    cf.supply_m1, cf.supply_m2, cf.supply_m3, cf.supply_m4, cf.supply_m5, cf.supply_m6, cf.supply_m7, cf.supply_m8, -- Supply fields
                    cf.balance_m1, cf.balance_m2, cf.balance_m3, cf.balance_m4, cf.balance_m5, cf.balance_m6, cf.balance_m7, cf.balance_m8, -- Balance fields
                    
                    (CASE
                        WHEN cf.balance_m1 < 0 THEN (date_trunc('month', CURRENT_DATE)::date + interval '0 months')
                        WHEN cf.balance_m2 < 0 THEN (date_trunc('month', CURRENT_DATE)::date + interval '1 month')
                        WHEN cf.balance_m3 < 0 THEN (date_trunc('month', CURRENT_DATE)::date + interval '2 months')
                        WHEN cf.balance_m4 < 0 THEN (date_trunc('month', CURRENT_DATE)::date + interval '3 months')
                        WHEN cf.balance_m5 < 0 THEN (date_trunc('month', CURRENT_DATE)::date + interval '4 months')
                        WHEN cf.balance_m6 < 0 THEN (date_trunc('month', CURRENT_DATE)::date + interval '5 months')
                        WHEN cf.balance_m7 < 0 THEN (date_trunc('month', CURRENT_DATE)::date + interval '6 months')
                        WHEN cf.balance_m8 < 0 THEN (date_trunc('month', CURRENT_DATE)::date + interval '7 months')
                        ELSE NULL
                    END - (COALESCE(cf.min_lead_time_val, 0) || ' days')::interval)::date AS order_by_date_value

                FROM calculated_figures cf
                JOIN product_template pt ON cf.product_tmpl_id = pt.id
                -- Ensure one product.product representative, e.g., the first one by id
                LEFT JOIN product_product pp ON pp.product_tmpl_id = pt.id AND pp.id = (SELECT MIN(sub_pp.id) FROM product_product sub_pp WHERE sub_pp.product_tmpl_id = pt.id)
                LEFT JOIN purchase_orders_total pot ON pot.product_tmpl_id = cf.product_tmpl_id;
            """)