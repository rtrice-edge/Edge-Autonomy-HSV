from odoo import api, fields, models, tools, _
import logging

_logger = logging.getLogger(__name__)

class PurchaseRequestDashboard(models.Model):
    _name = 'purchase.request.dashboard'
    _description = 'Purchase Request Efficiency Dashboard'
    _auto = False

    # Fields for grouping and display
    month = fields.Char(string='Month', readonly=True)
    year = fields.Char(string='Year', readonly=True)
    month_year = fields.Char(string='Month-Year', readonly=True)
    month_name = fields.Char(string='Month Name', readonly=True)
    
    # Time fields - define as Float instead of using group_operator which may cause issues
    draft_time = fields.Float(string='Draft Time (hrs)', readonly=True)
    validation_time = fields.Float(string='Validation Time (hrs)', readonly=True)
    approval_time = fields.Float(string='Approval Time (hrs)', readonly=True)
    po_creation_time = fields.Float(string='PO Creation Time (hrs)', readonly=True)
    total_time = fields.Float(string='Total Time (hrs)', readonly=True)
    pr_count = fields.Integer(string='Number of PRs', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    MIN(pr.id) as id,
                    TO_CHAR(COALESCE(pr.po_create_date, CURRENT_DATE), 'MM') AS month,
                    TO_CHAR(COALESCE(pr.po_create_date, CURRENT_DATE), 'YYYY') AS year,
                    TO_CHAR(COALESCE(pr.po_create_date, CURRENT_DATE), 'MM-YYYY') AS month_year,
                    TO_CHAR(COALESCE(pr.po_create_date, CURRENT_DATE), 'Month') AS month_name,
                    
                    -- Draft time: from creation to submission (in hours)
                    AVG(EXTRACT(EPOCH FROM (COALESCE(pr.submit_date, CURRENT_TIMESTAMP) - pr.create_date))/(60*60)) AS draft_time,
                    
                    -- Validation time: from submission to validation (in hours)
                    AVG(EXTRACT(EPOCH FROM (COALESCE(pr.validate_date, CURRENT_TIMESTAMP) - COALESCE(pr.submit_date, pr.create_date)))/(60*60)) AS validation_time,
                    
                    -- Approval time: from validation to approval (in hours)
                    AVG(EXTRACT(EPOCH FROM (COALESCE(pr.approve_date, CURRENT_TIMESTAMP) - COALESCE(pr.validate_date, pr.submit_date, pr.create_date)))/(60*60)) AS approval_time,
                    
                    -- PO creation time: from approval to PO creation (in hours)
                    AVG(EXTRACT(EPOCH FROM (COALESCE(pr.po_create_date, CURRENT_TIMESTAMP) - COALESCE(pr.approve_date, pr.validate_date, pr.submit_date, pr.create_date)))/(60*60)) AS po_creation_time,
                    
                    -- Total time: from creation to PO creation (in hours)
                    AVG(EXTRACT(EPOCH FROM (COALESCE(pr.po_create_date, CURRENT_TIMESTAMP) - pr.create_date))/(60*60)) AS total_time,
                    
                    -- Count of PRs
                    COUNT(pr.id) AS pr_count
                FROM
                    purchase_request pr
                WHERE
                    pr.state = 'po_created'
                GROUP BY 
                    TO_CHAR(COALESCE(pr.po_create_date, CURRENT_DATE), 'MM'),
                    TO_CHAR(COALESCE(pr.po_create_date, CURRENT_DATE), 'YYYY'),
                    TO_CHAR(COALESCE(pr.po_create_date, CURRENT_DATE), 'MM-YYYY'),
                    TO_CHAR(COALESCE(pr.po_create_date, CURRENT_DATE), 'Month')
                ORDER BY
                    year DESC, month DESC
            )
        """ % (self._table,))