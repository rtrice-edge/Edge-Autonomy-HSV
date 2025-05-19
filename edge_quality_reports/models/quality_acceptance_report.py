from odoo import models, fields, tools, api, _
from datetime import datetime, time, timedelta
import logging

_logger = logging.getLogger(__name__)

class QualityAcceptanceReport(models.Model):
    _name = 'quality.acceptance.report'
    _description = 'Vendor Quality Acceptance Performance Report'
    _auto = False

    # --- Fields for individual quality check lines ---
    partner_id = fields.Many2one('res.partner', string='Vendor', readonly=True)
    partner_name = fields.Char(string='Vendor', readonly=True)
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order', readonly=True)
    purchase_order_name = fields.Char(string='PO Reference', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_name = fields.Char(string='Product', readonly=True)
    control_date = fields.Datetime(string='Check Date', readonly=True)
    quality_state = fields.Selection([
        ('none', 'To do'),
        ('pass', 'Passed'),
        ('fail', 'Failed')
    ], string='Quality Status', readonly=True)
    is_passed = fields.Boolean(string='Is Passed', readonly=True)
    is_failed = fields.Boolean(string='Is Failed', readonly=True)
    job = fields.Char(string='Job', readonly=True)
    expense_type = fields.Char(string='Expense Type', readonly=True)
    move_id = fields.Many2one('stock.move', string='Stock Move', readonly=True)
    move_line_id = fields.Many2one('stock.move.line', string='Stock Move Line', readonly=True)
    qc_id = fields.Integer(string='Quality Check ID', readonly=True)
    team_id = fields.Many2one('quality.alert.team', string='Quality Team', readonly=True)
    point_id = fields.Many2one('quality.point', string='Quality Point', readonly=True)
    test_type_id = fields.Many2one('quality.point.test_type', string='Test Type', readonly=True)
    
    # --- Fields for dynamic aggregation by Odoo views (e.g., Pivot) ---
    # This field will be 1.0 if passed, 0.0 if failed. Averaging it gives the acceptance percentage.
    acceptance_rate = fields.Float(string='Acceptance Rate', readonly=True, group_operator='avg')
    
    # This field will be 1 for every line. Summing it gives the total number of quality checks.
    check_count = fields.Integer(string='Total Checks Count', readonly=True, group_operator='sum')
    
    # This field will be 1 if passed, 0 if not. Summing it gives the total passed quality checks.
    passed_count = fields.Integer(string='Passed Checks Count', readonly=True, group_operator='sum')
    
    # This field will be 1 if failed, 0 if not. Summing it gives the total failed quality checks.
    failed_count = fields.Integer(string='Failed Checks Count', readonly=True, group_operator='sum')

    def init(self):
        _logger.info("Initializing Quality Acceptance Report SQL view")
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        # Log the SQL query for debugging
        query = """
        CREATE OR REPLACE VIEW {} AS (
            WITH quality_data AS (
                SELECT
                    qc.id AS qc_id,
                    qc.team_id,
                    qc.point_id,
                    qc.test_type_id,
                    qc.control_date,
                    qc.quality_state,
                    qc.product_id,
                    pt.name AS product_name,
                    qc.picking_id,
                    qc.move_id,
                    qc.move_line_id,
                    
                    -- Get partner from multiple paths
                    COALESCE(
                        sp.partner_id,
                        po_partner.id
                    ) AS partner_id,
                    
                    COALESCE(
                        rp.name,
                        po_partner.name,
                        'Unknown Vendor'
                    ) AS partner_name,
                    
                    po.id AS purchase_order_id,
                    po.name AS purchase_order_name,
                    
                    -- Safe handling of job field to prevent errors
                    CASE
                        WHEN pol.job IS NULL THEN 'Unknown'
                        -- Check if job is a numeric string (reference to job model)
                        WHEN pol.job ~ '^[0-9]+' THEN COALESCE(j.name, 'Unknown')
                        -- If job is a direct string
                        ELSE pol.job
                    END AS job,
                    
                    -- Safe handling of expense_type
                    COALESCE(pol.expense_type, 'Unknown') AS expense_type,
                    
                    -- Determine if the quality check passed or failed
                    qc.quality_state = 'pass' AS is_passed,
                    qc.quality_state = 'fail' AS is_failed
                FROM
                    quality_check qc
                -- Left joins to get picking and partner
                LEFT JOIN
                    stock_picking sp ON qc.picking_id = sp.id
                LEFT JOIN
                    res_partner rp ON sp.partner_id = rp.id
                    
                -- Get stock move information
                LEFT JOIN
                    stock_move sm ON qc.move_id = sm.id
                LEFT JOIN
                    stock_move_line sml ON qc.move_line_id = sml.id
                    
                -- Get related purchase order through multiple paths
                LEFT JOIN (
                    -- First path: Through stock picking relation
                    SELECT po_rel.id, posp.stock_picking_id
                    FROM purchase_order po_rel
                    JOIN purchase_order_stock_picking_rel posp ON po_rel.id = posp.purchase_order_id
                    
                    UNION ALL
                    
                    -- Second path: Through stock move's purchase line
                    SELECT pol_po.order_id AS id, sm_po.picking_id 
                    FROM stock_move sm_po
                    JOIN purchase_order_line pol_po ON sm_po.purchase_line_id = pol_po.id
                    WHERE sm_po.picking_id IS NOT NULL
                ) picking_to_po ON sp.id = picking_to_po.stock_picking_id
                
                -- Get purchase order directly from move's purchase line
                LEFT JOIN (
                    SELECT order_id, id FROM purchase_order_line
                ) pol_to_po ON sm.purchase_line_id = pol_to_po.id
                
                -- Combine all possible paths to purchase order
                LEFT JOIN purchase_order po ON (
                    picking_to_po.id = po.id OR 
                    pol_to_po.order_id = po.id
                )
                
                -- Get partner from purchase order as fallback
                LEFT JOIN res_partner po_partner ON po.partner_id = po_partner.id
                
                -- Get purchase order line from move or move line
                LEFT JOIN purchase_order_line pol ON (
                    (sm.purchase_line_id = pol.id) OR
                    (sml.id IS NOT NULL AND sml.move_id IS NOT NULL AND 
                     EXISTS (SELECT 1 FROM stock_move sm_inner WHERE sm_inner.id = sml.move_id AND sm_inner.purchase_line_id = pol.id))
                )
                
                -- Join to product
                LEFT JOIN product_product pp ON qc.product_id = pp.id
                LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
                
                -- Safe join to job table
                LEFT JOIN job j ON (pol.job ~ '^[0-9]+' AND CAST(pol.job AS INTEGER) = j.id)
                
                WHERE
                    qc.quality_state IN ('pass', 'fail')
                    AND qc.control_date IS NOT NULL
            )
            SELECT
                ROW_NUMBER() OVER () AS id,
                qd.qc_id,
                qd.team_id,
                qd.point_id,
                qd.test_type_id,
                qd.partner_id,
                qd.partner_name,
                qd.purchase_order_id,
                qd.purchase_order_name,
                qd.product_id,
                qd.product_name,
                qd.control_date,
                qd.quality_state,
                qd.is_passed,
                qd.is_failed,
                qd.job,
                qd.expense_type,
                qd.move_id,
                qd.move_line_id,
                -- Fields for aggregation
                CASE WHEN qd.is_passed THEN 1.0 ELSE 0.0 END AS acceptance_rate,
                1 AS check_count,
                CASE WHEN qd.is_passed THEN 1 ELSE 0 END AS passed_count,
                CASE WHEN qd.is_failed THEN 1 ELSE 0 END AS failed_count
            FROM
                quality_data qd
        )
        """.format(self._table)
        
        _logger.info("Executing SQL query for Quality Acceptance Report view creation")
        try:
            self.env.cr.execute(query)
            _logger.info("Successfully created Quality Acceptance Report view")
        except Exception as e:
            _logger.error("Error creating Quality Acceptance Report view: %s", e)
            raise

class QualityAcceptanceWizard(models.TransientModel):
    _name = 'quality.acceptance.wizard'
    _description = 'Select parameters for Quality Acceptance Report'

    date_start = fields.Date(string='Start Date', required=True, default=lambda self: fields.Date.context_today(self) - timedelta(days=30))
    date_end = fields.Date(string='End Date', required=True, default=lambda self: fields.Date.context_today(self), help="End date is inclusive")
    team_ids = fields.Many2many('quality.alert.team', string='Quality Teams')

    def action_open_report(self):
        _logger.info("Opening Quality Acceptance Report with wizard parameters: start=%s, end=%s, teams=%s,",
                     self.date_start, self.date_end, self.team_ids.ids)
        
        domain = []
        
        if self.date_start:
            # Convert date to datetime string at start of day
            start_datetime = datetime.combine(self.date_start, time.min)
            domain.append(('control_date', '>=', fields.Datetime.to_string(start_datetime)))
        
        if self.date_end:
            # Convert date to datetime string at end of day
            end_datetime = datetime.combine(self.date_end, time.max)
            domain.append(('control_date', '<=', fields.Datetime.to_string(end_datetime)))
            
        if self.team_ids:
            domain.append(('team_id', 'in', self.team_ids.ids))
        
        context = {
            'pivot_measures': ['acceptance_rate', 'check_count', 'passed_count', 'failed_count'],
            'pivot_row_groupby': ['partner_name'],
            'pivot_column_groupby': [],
            'search_default_groupby_partner': 1,
        }
        
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Vendor Quality Acceptance Performance',
            'res_model': 'quality.acceptance.report',
            'view_mode': 'pivot,tree,graph',
            'domain': domain,
            'context': context,
        }
        
        _logger.info("Returning action with domain: %s", domain)
        return action