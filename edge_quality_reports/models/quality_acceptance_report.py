# -*- coding: utf-8 -*-

from odoo import models, fields, tools, api
from datetime import datetime, time


class QualityAcceptanceReport(models.Model):
    _name = 'quality.acceptance.report'
    _description = 'Vendor Quality Acceptance Report'
    _auto = False
    _order = 'control_date desc'
    
    # Fields for reporting
    partner_id = fields.Many2one('res.partner', string='Vendor', readonly=True)
    partner_name = fields.Char(string='Vendor Name', readonly=True)
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order', readonly=True)
    purchase_order_name = fields.Char(string='PO Reference', readonly=True)
    picking_id = fields.Many2one('stock.picking', string='Receipt', readonly=True)
    quality_check_id = fields.Many2one('quality.check', string='Quality Check', readonly=True)
    quality_check_name = fields.Char(string='Quality Check Reference', readonly=True)
    control_date = fields.Datetime(string='Check Date', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_name = fields.Char(string='Product Name', readonly=True)
    quality_state = fields.Selection([
        ('none', 'To do'),
        ('pass', 'Passed'),
        ('fail', 'Failed')
    ], string='Status', readonly=True)
    
    # Fields for aggregation
    check_count = fields.Integer(string='Total Checks', readonly=True, group_operator='sum')
    passed_count = fields.Integer(string='Passed Checks', readonly=True, group_operator='sum')
    failed_count = fields.Integer(string='Failed Checks', readonly=True, group_operator='sum')
    acceptance_rate = fields.Float(string='Acceptance Rate (%)', readonly=True, group_operator='avg')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
        CREATE OR REPLACE VIEW {} AS (
            WITH product_names AS (
                SELECT 
                    pp.id AS product_id,
                    CASE
                        WHEN pt.name IS NULL THEN 'Unknown'
                        WHEN jsonb_typeof(pt.name) = 'string' THEN pt.name::text
                        WHEN jsonb_typeof(pt.name) = 'object' THEN COALESCE(
                            pt.name->>'en_US',
                            pt.name->>'en',
                            (pt.name->>0),
                            'Unknown'
                        )
                        ELSE 'Unknown'
                    END AS name
                FROM product_product pp
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
            )
            SELECT
                row_number() OVER () AS id,
                qc.id AS quality_check_id,
                qc.name AS quality_check_name,
                qc.control_date,
                qc.picking_id,
                qc.product_id,
                pn.name AS product_name,
                qc.quality_state,
                
                po.id AS purchase_order_id,
                po.name AS purchase_order_name,
                
                rp.id AS partner_id,
                rp.name AS partner_name,
                
                -- Aggregation fields
                1 AS check_count,
                CASE WHEN qc.quality_state = 'pass' THEN 1 ELSE 0 END AS passed_count,
                CASE WHEN qc.quality_state = 'fail' THEN 1 ELSE 0 END AS failed_count,
                CASE WHEN qc.quality_state = 'pass' THEN 100.0 ELSE 0.0 END AS acceptance_rate
                
            FROM
                quality_check qc
            LEFT JOIN
                stock_picking sp ON qc.picking_id = sp.id
            LEFT JOIN
                purchase_order po ON (sp.origin = po.name OR sp.origin LIKE CONCAT(po.name, '%%'))
            LEFT JOIN
                res_partner rp ON po.partner_id = rp.id
            LEFT JOIN
                product_names pn ON qc.product_id = pn.product_id
            WHERE
                qc.quality_state IN ('pass', 'fail')
                AND sp.id IS NOT NULL
                AND po.id IS NOT NULL
                AND rp.id IS NOT NULL
            ORDER BY qc.control_date DESC
        )
        """.format(self._table))

class QualityAcceptanceWizard(models.TransientModel):
    _name = 'quality.acceptance.wizard'
    _description = 'Select parameters for Quality Acceptance Report'

    date_start = fields.Date(string='Start Date', required=True, 
                           default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_end = fields.Date(string='End Date', required=True,
                         default=fields.Date.context_today)
    partner_ids = fields.Many2many('res.partner', string='Vendors', domain=[('supplier_rank', '>', 0)],
                               help="Leave empty to include all vendors")
    product_ids = fields.Many2many('product.product', string='Products',
                               help="Leave empty to include all products")

    def action_open_report(self):
        """Open the Quality Acceptance Report with the specified filters"""
        self.ensure_one()
        domain = []
        
        if self.date_start:
            start_datetime = datetime.combine(self.date_start, time.min)
            domain.append(('control_date', '>=', fields.Datetime.to_string(start_datetime)))
        
        if self.date_end:
            end_datetime = datetime.combine(self.date_end, time.max)
            domain.append(('control_date', '<=', fields.Datetime.to_string(end_datetime)))
        
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
            
        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))
            
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
                'order': 'control_date desc',
                'search_default_groupby_partner': 1,
            },
        }