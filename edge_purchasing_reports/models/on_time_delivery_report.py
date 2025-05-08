from odoo import models, fields, tools, api
from datetime import timedelta, datetime
import pytz
import logging

_logger = logging.getLogger(__name__)

class OnTimeDeliveryReport(models.Model):
    _name = 'on.time.delivery.report'
    _description = 'Supplier On-Time Delivery Performance Report'
    _auto = False
    _order = 'on_time_percentage desc'

    partner_id = fields.Many2one('res.partner', string='Vendor', readonly=True)
    partner_name = fields.Char(string='Vendor Name', readonly=True)
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order', readonly=True)
    purchase_order_name = fields.Char(string='Purchase Order Reference', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_name = fields.Char(string='Product Name', readonly=True)
    job = fields.Char(string='Job', readonly=True)
    product_qty = fields.Float(string='Quantity', readonly=True)
    date_planned = fields.Datetime(string='Expected Delivery', readonly=True)
    effective_date = fields.Datetime(string='Latest Delivery', readonly=True)
    is_on_time = fields.Boolean(string='Is On Time', readonly=True)
    is_late = fields.Boolean(string='Is Late', readonly=True)
    days_late = fields.Integer(string='Days Late', readonly=True)
    on_time_percentage = fields.Float(string='On-Time %', readonly=True, group_operator='avg')
    total_deliveries = fields.Integer(string='Total Deliveries', readonly=True)
    on_time_deliveries = fields.Integer(string='On-Time Deliveries', readonly=True)
    
    # Storing the filter parameters at class level
    _date_start = None
    _date_end = None
    _production_only = None

    def init(self):
        # The initial creation will happen with default empty filters
        # The actual view will be refreshed when the report is run with specific parameters
        tools.drop_view_if_exists(self.env.cr, 'on_time_delivery_report')
        self._create_report_view()

    def _create_report_view(self):
        date_start_clause = ''
        date_end_clause = ''
        production_only_clause = ''
        
        if self._date_start:
            date_start_clause = f"AND pol.effective_date >= '{self._date_start}'"
        
        if self._date_end:
            date_end_clause = f"AND pol.effective_date <= '{self._date_end}'"
            
        if self._production_only:
            production_only_clause = "AND j.name::json ->> 'en_US' = 'Inventory (Raw Materials)'"
        
        # Create the SQL view with the dynamic filters
        self.env.cr.execute(f"""
        CREATE OR REPLACE VIEW on_time_delivery_report AS (
            WITH filtered_deliveries AS (
                SELECT
                    pol.id AS pol_id,
                    po.partner_id,
                    rp.name AS partner_name,
                    po.id AS purchase_order_id,
                    po.name AS purchase_order_name,
                    pol.product_id,
                    (pt.name::json ->> 'en_US') AS product_name,
                    CASE
                        WHEN j.name IS NOT NULL THEN (j.name::json ->> 'en_US')
                        WHEN pol.job = 'Unknown' OR pol.job IS NULL THEN 'Unknown'
                        ELSE 'Unknown'
                    END AS job,
                    pol.product_qty,
                    pol.date_planned,
                    pol.effective_date,
                    CASE 
                        WHEN pol.effective_date IS NULL THEN false
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
                    job j ON pol.job = CAST(j.id AS varchar)
                WHERE
                    pol.display_type IS NULL
                    AND po.state IN ('purchase', 'done')
                    AND pol.effective_date IS NOT NULL
                    {date_start_clause}
                    {date_end_clause}
                    {production_only_clause}
            ),
            vendor_stats AS (
                SELECT
                    partner_id,
                    COUNT(*) AS total_deliveries,
                    SUM(CASE WHEN is_on_time THEN 1 ELSE 0 END) AS on_time_deliveries,
                    CASE 
                        WHEN COUNT(*) > 0 THEN 
                            (SUM(CASE WHEN is_on_time THEN 1 ELSE 0 END)::float / COUNT(*)::float)
                        ELSE 0.0
                    END AS on_time_percentage
                FROM
                    filtered_deliveries
                GROUP BY
                    partner_id
            )
            SELECT
                ROW_NUMBER() OVER () AS id,
                fd.pol_id,
                fd.partner_id,
                fd.partner_name,
                fd.purchase_order_id,
                fd.purchase_order_name,
                fd.product_id,
                fd.product_name,
                fd.job,
                fd.product_qty,
                fd.date_planned,
                fd.effective_date,
                fd.is_on_time,
                fd.is_late,
                fd.days_late,
                vs.on_time_percentage,
                vs.total_deliveries,
                vs.on_time_deliveries
            FROM
                filtered_deliveries fd
            JOIN
                vendor_stats vs ON fd.partner_id = vs.partner_id
        )
        """)
        _logger.info(f"Created on_time_delivery_report view with filters: date_start={self._date_start}, date_end={self._date_end}, production_only={self._production_only}")


class OnTimeDeliveryWizard(models.TransientModel):
    _name = 'on.time.delivery.wizard'
    _description = 'Select parameters for On-Time Delivery Report'

    date_start = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date', required=True)
    production_items_only = fields.Boolean(string='Production Items Only', default=True,
                                          help="Show only Raw Materials for production")

    def action_open_report(self):
        # Store filter parameters at class level in the report model
        report_model = self.env['on.time.delivery.report']
        report_model._date_start = self.date_start
        report_model._date_end = self.date_end
        report_model._production_only = self.production_items_only
        
        # Recreate the SQL view with the new filters
        report_model._create_report_view()
        
        # Return action to open the report - no domain filters needed now
        # as the filtering is done at the SQL level
        return {
            'type': 'ir.actions.act_window',
            'name': 'Supplier On-Time Delivery Performance',
            'res_model': 'on.time.delivery.report',
            'view_mode': 'pivot,tree,graph',
            'context': {
                'pivot_measures': ['on_time_percentage', 'total_deliveries', 'on_time_deliveries'],
                'pivot_row_groupby': ['partner_name'],
                'pivot_column_groupby': ['purchase_order_name'],
                'search_default_groupby_partner': 1,
            },
        }