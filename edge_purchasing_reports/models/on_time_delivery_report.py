from odoo import models, fields, tools, api
from datetime import timedelta

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

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'on_time_delivery_report')
        self.env.cr.execute("""
        CREATE OR REPLACE VIEW on_time_delivery_report AS (
            WITH delivery_stats AS (
                SELECT
                    pol.id AS pol_id,
                    po.partner_id,
                    rp.name AS partner_name,
                    po.id AS purchase_order_id,
                    po.name AS purchase_order_name,
                    pol.product_id,
                    pt.name AS product_name,
                    pol.job AS job,
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
                WHERE
                    pol.display_type IS NULL
                    AND po.state IN ('purchase', 'done')
                    AND pol.effective_date IS NOT NULL
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
                    delivery_stats
                GROUP BY
                    partner_id
            )
            SELECT
                ROW_NUMBER() OVER () AS id,
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
                vs.on_time_percentage,
                vs.total_deliveries,
                vs.on_time_deliveries
            FROM
                delivery_stats ds
            JOIN
                vendor_stats vs ON ds.partner_id = vs.partner_id
        )
        """)


class OnTimeDeliveryWizard(models.TransientModel):
    _name = 'on.time.delivery.wizard'
    _description = 'Select parameters for On-Time Delivery Report'

    date_start = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date', required=True)
    production_items_only = fields.Boolean(string='Production Items Only', default=True,
                                          help="Show only Raw Materials for production")

    def action_open_report(self):
        # Build domain based on wizard inputs
        domain = []
        
        if self.date_start:
            domain.append(('effective_date', '>=', self.date_start))
        if self.date_end:
            # Add one day to include the end date fully
            end_date_inclusive = fields.Datetime.to_string(
                fields.Datetime.from_string(fields.Datetime.to_string(self.date_end)) + 
                timedelta(days=1)
            )
            domain.append(('effective_date', '<', end_date_inclusive))
            
        if self.production_items_only:
            domain.append(('job', '=', 'raw_materials'))
            
        # Return action to open the report with the specified domain
        return {
            'type': 'ir.actions.act_window',
            'name': 'Supplier On-Time Delivery Performance',
            'res_model': 'on.time.delivery.report',
            'view_mode': 'pivot,tree,graph',
            'domain': domain,
            'context': {
                'pivot_measures': ['on_time_percentage', 'total_deliveries', 'on_time_deliveries'],
                'pivot_row_groupby': ['partner_name'],
                'pivot_column_groupby': ['purchase_order_name'],
                'search_default_groupby_partner': 1,
                'no_breadcrumbs': True
            },
        }