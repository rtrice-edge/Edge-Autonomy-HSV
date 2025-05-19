from odoo import models, fields, tools, api
from datetime import datetime, time

class QualityAcceptanceReport(models.Model):
    _name = 'quality.acceptance.report'
    _description = 'Quality Acceptance Performance Report by Vendor'
    _auto = False

    # --- Vendor Information ---
    partner_id = fields.Many2one('res.partner', string='Vendor', readonly=True)
    partner_name = fields.Char(string='Vendor Name', readonly=True)
    
    # --- Quality Check Information ---
    quality_check_id = fields.Many2one('quality.check', string='Quality Check', readonly=True)
    quality_check_name = fields.Char(string='Quality Check Name', readonly=True)
    quality_state = fields.Selection([
        ('pass', 'Passed'),
        ('fail', 'Failed'),
    ], string='Quality State', readonly=True)
    control_date = fields.Datetime(string='Check Date', readonly=True)
    
    # --- Purchase Order Information (may be null) ---
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order', readonly=True)
    purchase_order_name = fields.Char(string='PO Reference', readonly=True)
    purchase_line_id = fields.Many2one('purchase.order.line', string='Purchase Line', readonly=True)
    job = fields.Char(string='Job', readonly=True)
    expense_type = fields.Char(string='Expense Type', readonly=True)
    
    # --- Product Information ---
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_name = fields.Char(string='Product Name', readonly=True)
    
    # --- Aggregation Fields ---
    total_checks = fields.Integer(string='Total Quality Checks', readonly=True, group_operator='sum')
    passed_checks = fields.Integer(string='Passed Checks', readonly=True, group_operator='sum')
    failed_checks = fields.Integer(string='Failed Checks', readonly=True, group_operator='sum')
    acceptance_rate = fields.Float(string='Acceptance Rate (%)', readonly=True, group_operator='avg')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
        CREATE OR REPLACE VIEW {} AS (
            WITH quality_with_po AS (
                SELECT
                    qc.id AS quality_check_id,
                    qc.name AS quality_check_name,
                    qc.quality_state,
                    qc.control_date,
                    qc.product_id,
                    qc.picking_id,
                    qc.move_id,
                    qc.move_line_id,
                    
                    -- Try to find purchase order through multiple paths
                    COALESCE(
                        -- Path 1: Direct through move_id
                        sm_direct.purchase_line_id,
                        -- Path 2: Through move_line_id -> move_id
                        sm_moveline.purchase_line_id,
                        -- Path 3: Through picking_id -> move_ids
                        sm_picking.purchase_line_id
                    ) AS purchase_line_id,
                    
                    -- Get the vendor - try multiple paths
                    COALESCE(
                        -- From direct purchase order
                        po_direct.partner_id,
                        -- From purchase order through move_line
                        po_moveline.partner_id,
                        -- From purchase order through picking
                        po_picking.partner_id,
                        -- From picking partner (fallback)
                        sp.partner_id
                    ) AS vendor_id
                    
                FROM quality_check qc
                
                -- Path 1: Direct move_id to purchase_line_id
                LEFT JOIN stock_move sm_direct ON qc.move_id = sm_direct.id
                LEFT JOIN purchase_order_line pol_direct ON sm_direct.purchase_line_id = pol_direct.id
                LEFT JOIN purchase_order po_direct ON pol_direct.order_id = po_direct.id
                
                -- Path 2: Through move_line_id -> move_id -> purchase_line_id
                LEFT JOIN stock_move_line sml ON qc.move_line_id = sml.id
                LEFT JOIN stock_move sm_moveline ON sml.move_id = sm_moveline.id
                LEFT JOIN purchase_order_line pol_moveline ON sm_moveline.purchase_line_id = pol_moveline.id
                LEFT JOIN purchase_order po_moveline ON pol_moveline.order_id = po_moveline.id
                
                -- Path 3: Through picking_id -> moves -> purchase_line_id
                LEFT JOIN stock_picking sp ON qc.picking_id = sp.id
                LEFT JOIN stock_move sm_picking ON sp.id = sm_picking.picking_id AND qc.product_id = sm_picking.product_id
                LEFT JOIN purchase_order_line pol_picking ON sm_picking.purchase_line_id = pol_picking.id
                LEFT JOIN purchase_order po_picking ON pol_picking.order_id = po_picking.id
                
                WHERE qc.quality_state IN ('pass', 'fail')
            ),
            quality_stats AS (
                SELECT
                    qwp.quality_check_id,
                    qwp.quality_check_name,
                    qwp.quality_state,
                    qwp.control_date,
                    qwp.product_id,
                    qwp.purchase_line_id,
                    qwp.vendor_id,
                    
                    -- Get vendor info
                    rp.name AS partner_name,
                    
                    -- Get purchase order info
                    pol.order_id AS purchase_order_id,
                    po.name AS purchase_order_name,
                    pol.job,
                    pol.expense_type,
                    
                    -- Get product info
                    COALESCE(
                        (pt.name::json ->> 'en_US'),
                        pt.name::varchar,
                        pp.default_code,
                        'Unknown Product'
                    ) AS product_name,
                    
                    -- Aggregation fields
                    1 AS total_checks,
                    CASE WHEN qwp.quality_state = 'pass' THEN 1 ELSE 0 END AS passed_checks,
                    CASE WHEN qwp.quality_state = 'fail' THEN 1 ELSE 0 END AS failed_checks,
                    CASE WHEN qwp.quality_state = 'pass' THEN 100.0 ELSE 0.0 END AS acceptance_rate
                    
                FROM quality_with_po qwp
                LEFT JOIN res_partner rp ON qwp.vendor_id = rp.id
                LEFT JOIN purchase_order_line pol ON qwp.purchase_line_id = pol.id
                LEFT JOIN purchase_order po ON pol.order_id = po.id
                LEFT JOIN product_product pp ON qwp.product_id = pp.id
                LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
            )
            SELECT
                ROW_NUMBER() OVER () AS id,
                qs.quality_check_id,
                qs.quality_check_name,
                qs.quality_state,
                qs.control_date,
                qs.vendor_id AS partner_id,
                qs.partner_name,
                qs.purchase_order_id,
                qs.purchase_order_name,
                qs.purchase_line_id,
                qs.job,
                qs.expense_type,
                qs.product_id,
                qs.product_name,
                qs.total_checks,
                qs.passed_checks,
                qs.failed_checks,
                qs.acceptance_rate
            FROM quality_stats qs
        )
        """.format(self._table))


class QualityAcceptanceWizard(models.TransientModel):
    _name = 'quality.acceptance.wizard'
    _description = 'Quality Acceptance Report Parameters'

    date_start = fields.Date(string='Start Date', required=True, 
                           default=lambda self: fields.Date.today().replace(day=1))
    date_end = fields.Date(string='End Date', required=True, 
                         default=fields.Date.today())
    vendor_ids = fields.Many2many('res.partner', string='Vendors', 
                                 domain=[('supplier_rank', '>', 0)],
                                 help="Leave empty to include all vendors")
    product_ids = fields.Many2many('product.product', string='Products',
                                  help="Leave empty to include all products")
    include_no_vendor = fields.Boolean(string='Include checks without vendor', 
                                      default=False,
                                      help="Include quality checks that couldn't be linked to a vendor")

    def action_open_report(self):
        domain = []
        
        # Date filters
        if self.date_start:
            start_datetime = datetime.combine(self.date_start, time.min)
            domain.append(('control_date', '>=', fields.Datetime.to_string(start_datetime)))
        if self.date_end:
            end_datetime = datetime.combine(self.date_end, time.max)
            domain.append(('control_date', '<=', fields.Datetime.to_string(end_datetime)))
            
        # Vendor filter
        if self.vendor_ids:
            domain.append(('partner_id', 'in', self.vendor_ids.ids))
        elif not self.include_no_vendor:
            domain.append(('partner_id', '!=', False))
            
        # Product filter
        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))
            
        return {
            'type': 'ir.actions.act_window',
            'name': 'Quality Acceptance Performance by Vendor',
            'res_model': 'quality.acceptance.report',
            'view_mode': 'pivot,tree,graph',
            'domain': domain,
            'context': {
                'pivot_measures': ['acceptance_rate', 'total_checks', 'passed_checks', 'failed_checks'],
                'pivot_row_groupby': ['partner_name'],
                'pivot_column_groupby': ['quality_state'],
                'search_default_groupby_vendor': 1,
            },
        }