from odoo import models, fields, tools, api
from datetime import datetime, time, timedelta

class OnTimeDeliveryReport(models.Model):
    _name = 'on.time.delivery.report'
    _description = 'Supplier On-Time Delivery Performance Report'
    _auto = False
    # _order removed as global on-time percentage is no longer a direct field
    # Consider setting a default order in the action or view if needed e.g., 'effective_date desc'

    # --- Fields for individual delivery lines ---
    partner_id = fields.Many2one('res.partner', string='Vendor', readonly=True)
    partner_name = fields.Char(string='Vendor Name', readonly=True)
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order', readonly=True)
    purchase_order_name = fields.Char(string='Purchase Order Reference', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_name = fields.Char(string='Product Name', readonly=True)
    job = fields.Char(string='Job', readonly=True) # Used for "Production Items Only" filter
    product_qty = fields.Float(string='Quantity', readonly=True)
    date_planned = fields.Datetime(string='Expected Delivery', readonly=True)
    effective_date = fields.Datetime(string='Latest Delivery', readonly=True)
    is_on_time = fields.Boolean(string='Is On Time', readonly=True)
    is_late = fields.Boolean(string='Is Late', readonly=True)
    days_late = fields.Integer(string='Days Late', readonly=True)
    pol_id = fields.Integer(string='Purchase Order Line ID', readonly=True) # Storing POL ID

    # --- Fields for dynamic aggregation by Odoo views (e.g., Pivot) ---
    # This field will be 1.0 if on_time, 0.0 if not. Averaging it gives the on-time percentage.
    on_time_rate = fields.Float(string='On-Time Rate', readonly=True, group_operator='avg')
    
    # This field will be 1 for every line. Summing it gives the total number of deliveries.
    delivery_line_count = fields.Integer(string='Total Deliveries Count', readonly=True, group_operator='sum')
    
    # This field will be 1 if on_time, 0 if not. Summing it gives the total on-time deliveries.
    on_time_delivery_count = fields.Integer(string='On-Time Deliveries Count', readonly=True, group_operator='sum')


    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table) # Use self._table for view name
        self.env.cr.execute("""
        CREATE OR REPLACE VIEW {} AS (
            WITH delivery_stats AS (
                SELECT
                    pol.id AS pol_id,
                    po.partner_id,
                    rp.name AS partner_name,
                    po.id AS purchase_order_id,
                    po.name AS purchase_order_name,
                    pol.product_id,
                    (pt.name::json ->> 'en_US') AS product_name, -- Assuming product name is translatable
                    CASE
                        WHEN j.name IS NOT NULL THEN j.name
                        WHEN pol.job = 'Unknown' OR pol.job IS NULL THEN 'Unknown'
                        -- Consider if pol.job could hold other values that should be displayed
                        ELSE COALESCE(pol.job, 'Unknown') 
                    END AS job,
                    pol.product_qty,
                    pol.date_planned,
                    pol.effective_date,
                    CASE 
                        WHEN pol.effective_date IS NULL THEN false
                        -- Grace period of 7 days for on-time delivery
                        WHEN pol.effective_date <= (pol.date_planned + interval '7 days') THEN true
                        ELSE false
                    END AS is_on_time,
                    CASE 
                        WHEN pol.effective_date IS NULL THEN false
                        WHEN pol.effective_date > (pol.date_planned + interval '7 days') THEN true
                        ELSE false
                    END AS is_late,
                    CASE
                        WHEN pol.effective_date IS NULL THEN 0
                        WHEN pol.effective_date > pol.date_planned THEN 
                            EXTRACT(DAY FROM (pol.effective_date - pol.date_planned))::integer
                        ELSE 0
                    END AS days_late
                FROM
                    purchase_order_line pol
                JOIN
                    purchase_order po ON pol.order_id = po.id
                JOIN
                    res_partner rp ON po.partner_id = rp.id
                LEFT JOIN
                    product_product pp ON pol.product_id = pp.id
                LEFT JOIN
                    product_template pt ON pp.product_tmpl_id = pt.id
                LEFT JOIN
                    job j ON pol.job = CAST(j.id AS varchar) -- Ensure this join logic for 'job' is correct for your setup
                WHERE
                    pol.display_type IS NULL
                    AND po.state IN ('purchase', 'done')
                    AND pol.effective_date IS NOT NULL -- Only consider lines with an effective delivery date
            )
            SELECT
                ROW_NUMBER() OVER () AS id, -- Mandatory unique ID for the view
                ds.pol_id, -- Retain original POL ID if needed for drill-down or reference
                ds.partner_id,
                ds.partner_name,
                ds.purchase_order_id,
                ds.purchase_order_name,
                ds.product_id,
                ds.product_name,
                ds.job,
                ds.product_qty,
                ds.date_planned,
                ds.effective_date,
                ds.is_on_time,
                ds.is_late,
                ds.days_late,
                -- Fields for aggregation
                CASE WHEN ds.is_on_time THEN 1.0 ELSE 0.0 END AS on_time_rate,
                1 AS delivery_line_count,
                CASE WHEN ds.is_on_time THEN 1 ELSE 0 END AS on_time_delivery_count
            FROM
                delivery_stats ds
        )
        """.format(self._table))


class OnTimeDeliveryWizard(models.TransientModel):
    _name = 'on.time.delivery.wizard'
    _description = 'Select parameters for On-Time Delivery Report'

    date_start = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date', required=True, help="End date is inclusive")
    production_items_only = fields.Boolean(
        string='Production Items Only', 
        default=True, # Default can be true or false based on common use case
        help="Show only items where Job is 'Inventory (Raw Materials)'" # Clarified help text
    )

    def action_open_report(self):
        domain = []
        
        if self.date_start:
            # Convert date to datetime string at start of day
            start_datetime = datetime.combine(self.date_start, time.min)
            domain.append(('effective_date', '>=', fields.Datetime.to_string(start_datetime)))
        if self.date_end:
            # Convert date to datetime string at end of day
            end_datetime = datetime.combine(self.date_end, time.max)
            domain.append(('effective_date', '<=', fields.Datetime.to_string(end_datetime)))
            
        if self.production_items_only:
            domain.append(('job', '=', 'Inventory (Raw Materials)'))
            
        return {
            'type': 'ir.actions.act_window',
            'name': 'Supplier On-Time Delivery Performance',
            'res_model': 'on.time.delivery.report',
            'view_mode': 'pivot,tree,graph',
            'domain': domain,
            'context': {
                'pivot_measures': ['on_time_rate', 'delivery_line_count', 'on_time_delivery_count'],
                # Swap these two lines to change the axes
                'pivot_row_groupby': ['partner_name'],  # Vendors as rows
                'pivot_column_groupby': ['purchase_order_name', 'product_name'],  # PO and products as columns
                # Group by vendor in list view
                'search_default_groupby_partner': 1,
            },
        }