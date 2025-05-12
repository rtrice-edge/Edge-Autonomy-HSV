from odoo import models, fields, tools, api
from datetime import datetime, time, timedelta

class QualityAcceptanceReport(models.Model):
    _name = 'quality.acceptance.report'
    _description = 'Vendor Quality Acceptance Performance Report'
    _auto = False

    # --- Fields for individual quality check lines ---
    partner_id = fields.Many2one('res.partner', string='Vendor', readonly=True)
    partner_name = fields.Char(string='Vendor Name', readonly=True)
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order', readonly=True)
    purchase_order_name = fields.Char(string='PO Reference', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_name = fields.Char(string='Product Name', readonly=True)
    job = fields.Char(string='Job', readonly=True) # Used for "Production Items Only" filter
    quality_check_id = fields.Many2one('quality.check', string='Quality Check', readonly=True)
    quality_state = fields.Selection([
        ('none', 'To do'),
        ('pass', 'Passed'),
        ('fail', 'Failed')
    ], string='Status', readonly=True)
    control_date = fields.Datetime(string='Check Date', readonly=True)
    team_id = fields.Many2one('quality.alert.team', string='Team', readonly=True)
    test_type_id = fields.Many2one('quality.point.test_type', string='Test Type', readonly=True)
    is_passed = fields.Boolean(string='Is Passed', readonly=True)
    is_failed = fields.Boolean(string='Is Failed', readonly=True)

    # --- Fields for dynamic aggregation by Odoo views (e.g., Pivot) ---
    # This field will be 1.0 if passed, 0.0 if failed. Averaging it gives the acceptance percentage.
    acceptance_rate = fields.Float(string='Acceptance Rate', readonly=True, group_operator='avg')
    
    # This field will be 1 for every line. Summing it gives the total number of quality checks.
    check_count = fields.Integer(string='Total Checks Count', readonly=True, group_operator='sum')
    
    # This field will be 1 if passed, 0 if failed. Summing it gives the total passed checks.
    passed_count = fields.Integer(string='Passed Checks Count', readonly=True, group_operator='sum')

    # This field will be 1 if failed, 0 if passed. Summing it gives the total failed checks.
    failed_count = fields.Integer(string='Failed Checks Count', readonly=True, group_operator='sum')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
        CREATE OR REPLACE VIEW {} AS (
            WITH quality_stats AS (
                SELECT
                    qc.id AS quality_check_id,
                    -- Vendor information
                    COALESCE(po.partner_id, sm.partner_id) AS partner_id,
                    COALESCE(rp.name, 'Unknown') AS partner_name,
                    
                    -- Purchase Order information
                    po.id AS purchase_order_id,
                    COALESCE(po.name, '') AS purchase_order_name,
                    
                    -- Product information
                    qc.product_id,
                    -- Handle JSON product name properly
                    CASE 
                        WHEN pt.name IS NULL THEN 'Unknown'
                        WHEN jsonb_typeof(pt.name::jsonb) = 'object' THEN 
                            COALESCE(pt.name::jsonb->>'en_US', (pt.name::jsonb->>(jsonb_object_keys(pt.name::jsonb)))[0], 'Unknown')
                        ELSE pt.name::text
                    END AS product_name,
                    
                    -- Job information
                    CASE
                        WHEN j.id IS NOT NULL THEN j.name
                        WHEN pol.job = 'Inventory (Raw Materials)' THEN 'Inventory (Raw Materials)'
                        ELSE COALESCE(pol.job, 'Unknown')
                    END AS job,
                    
                    -- Quality information
                    qc.quality_state,
                    qc.control_date,
                    qc.team_id,
                    qc.test_type_id,
                    CASE 
                        WHEN qc.quality_state = 'pass' THEN true
                        ELSE false
                    END AS is_passed,
                    CASE 
                        WHEN qc.quality_state = 'fail' THEN true
                        ELSE false
                    END AS is_failed
                FROM
                    quality_check qc
                -- First try to get vendor from stock move
                LEFT JOIN 
                    stock_move sm ON qc.move_id = sm.id
                -- Then try through purchase line
                LEFT JOIN
                    purchase_order_line pol ON sm.purchase_line_id = pol.id
                LEFT JOIN
                    purchase_order po ON pol.order_id = po.id
                -- Get vendor name
                LEFT JOIN
                    res_partner rp ON COALESCE(po.partner_id, sm.partner_id) = rp.id
                -- Get product info
                LEFT JOIN
                    product_product pp ON qc.product_id = pp.id
                LEFT JOIN
                    product_template pt ON pp.product_tmpl_id = pt.id
                -- Get job info - ensure proper type casting
                LEFT JOIN
                    job j ON (pol.job IS NOT NULL AND CAST(pol.job AS VARCHAR) = CAST(j.id AS VARCHAR))
                WHERE
                    qc.quality_state IN ('pass', 'fail')
                    AND qc.control_date IS NOT NULL
            )
            SELECT
                ROW_NUMBER() OVER () AS id, -- Mandatory unique ID for the view
                qs.quality_check_id,
                qs.partner_id,
                qs.partner_name,
                qs.purchase_order_id,
                qs.purchase_order_name,
                qs.product_id,
                qs.product_name,
                qs.job,
                qs.quality_state,
                qs.control_date,
                qs.team_id,
                qs.test_type_id,
                qs.is_passed,
                qs.is_failed,
                -- Fields for aggregation
                CASE WHEN qs.is_passed THEN 1.0 ELSE 0.0 END AS acceptance_rate,
                1 AS check_count,
                CASE WHEN qs.is_passed THEN 1 ELSE 0 END AS passed_count,
                CASE WHEN qs.is_failed THEN 1 ELSE 0 END AS failed_count
            FROM
                quality_stats qs
        )
        """.format(self._table))


class QualityAcceptanceWizard(models.TransientModel):
    _name = 'quality.acceptance.wizard'
    _description = 'Select parameters for Quality Acceptance Report'

    date_start = fields.Date(string='Start Date', required=True, default=lambda self: fields.Date.context_today(self) - timedelta(days=30))
    date_end = fields.Date(string='End Date', required=True, default=lambda self: fields.Date.context_today(self), help="End date is inclusive")
    production_items_only = fields.Boolean(
        string='Production Items Only', 
        default=False,
        help="Show only items where Job is 'Inventory (Raw Materials)'"
    )

    def action_open_report(self):
        domain = []
        
        if self.date_start:
            # Convert date to datetime string at start of day
            start_datetime = datetime.combine(self.date_start, time.min)
            domain.append(('control_date', '>=', fields.Datetime.to_string(start_datetime)))
        if self.date_end:
            # Convert date to datetime string at end of day
            end_datetime = datetime.combine(self.date_end, time.max)
            domain.append(('control_date', '<=', fields.Datetime.to_string(end_datetime)))
            
        if self.production_items_only:
            domain.append(('job', '=', 'Inventory (Raw Materials)'))
            
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vendor Quality Acceptance Report',
            'res_model': 'quality.acceptance.report',
            'view_mode': 'pivot,tree,graph',
            'domain': domain,
            'context': {
                'pivot_measures': ['acceptance_rate', 'check_count', 'passed_count', 'failed_count'],
                'pivot_row_groupby': ['partner_name'],
                'pivot_column_groupby': [],
                'search_default_groupby_partner': 1,
            },
        }