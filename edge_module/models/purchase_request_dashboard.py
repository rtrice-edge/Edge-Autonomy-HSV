from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class PurchaseRequestDashboard(models.Model):
    _name = 'purchase.request.dashboard'
    _description = 'Purchase Request Efficiency Dashboard'
    _auto = False

    month = fields.Char(string='Month', readonly=True)
    year = fields.Char(string='Year', readonly=True)
    request_id = fields.Many2one('purchase.request', string='Purchase Request', readonly=True)
    draft_time = fields.Float(string='Draft Time (Days)', readonly=True, group_operator="avg")
    validation_time = fields.Float(string='Validation Time (Days)', readonly=True, group_operator="avg")
    approval_time = fields.Float(string='Approval Time (Days)', readonly=True, group_operator="avg")
    po_creation_time = fields.Float(string='PO Creation Time (Days)', readonly=True, group_operator="avg")
    total_time = fields.Float(string='Total Time (Days)', readonly=True, group_operator="avg")
    count = fields.Integer(string='Number of PRs', readonly=True)

    def init(self):
        tools = self.env['ir.model.data']
        self._cr.execute("""
            CREATE OR REPLACE VIEW purchase_request_dashboard AS (
                SELECT
                    pr.id AS id,
                    pr.id AS request_id,
                    TO_CHAR(COALESCE(pr.po_create_date, CURRENT_DATE), 'MM') AS month,
                    TO_CHAR(COALESCE(pr.po_create_date, CURRENT_DATE), 'YYYY') AS year,
                    -- Draft time: from creation to submission
                    EXTRACT(EPOCH FROM (COALESCE(pr.submit_date, CURRENT_TIMESTAMP) - pr.create_date))/(24*60*60) AS draft_time,
                    -- Validation time: from submission to validation
                    EXTRACT(EPOCH FROM (COALESCE(pr.validate_date, CURRENT_TIMESTAMP) - COALESCE(pr.submit_date, pr.create_date)))/(24*60*60) AS validation_time,
                    -- Approval time: from validation to approval
                    EXTRACT(EPOCH FROM (COALESCE(pr.approve_date, CURRENT_TIMESTAMP) - COALESCE(pr.validate_date, pr.submit_date, pr.create_date)))/(24*60*60) AS approval_time,
                    -- PO creation time: from approval to PO creation
                    EXTRACT(EPOCH FROM (COALESCE(pr.po_create_date, CURRENT_TIMESTAMP) - COALESCE(pr.approve_date, pr.validate_date, pr.submit_date, pr.create_date)))/(24*60*60) AS po_creation_time,
                    -- Total time
                    EXTRACT(EPOCH FROM (COALESCE(pr.po_create_date, CURRENT_TIMESTAMP) - pr.create_date))/(24*60*60) AS total_time,
                    1 AS count
                FROM
                    purchase_request pr
                WHERE
                    pr.state = 'po_created'
            )
        """)