from odoo import api, fields, models

class PurchaseRequestEfficiencyReport(models.Model):
    _name = 'purchase.request.efficiency.report'
    _description = 'Purchase Request Efficiency Report'
    _auto = False
    _rec_name = 'month'
    
    month = fields.Char(string='Month', readonly=True)
    draft_duration = fields.Float(string='Draft Duration (hrs)', readonly=True, group_operator="avg")
    validation_duration = fields.Float(string='Validation Duration (hrs)', readonly=True, group_operator="avg")
    approval_duration = fields.Float(string='Approval Duration (hrs)', readonly=True, group_operator="avg")
    po_creation_duration = fields.Float(string='PO Creation Duration (hrs)', readonly=True, group_operator="avg")
    total_duration = fields.Float(string='Total Duration (hrs)', readonly=True, group_operator="avg")
    count = fields.Integer(string='Number of PRs', readonly=True, group_operator="sum")
    
    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    MIN(id) as id,
                    to_char(COALESCE(po_create_date, CURRENT_DATE), 'YYYY-MM') AS month,
                    AVG(EXTRACT(EPOCH FROM (COALESCE(submit_date, CURRENT_TIMESTAMP) - create_date))/3600) AS draft_duration,
                    AVG(EXTRACT(EPOCH FROM (COALESCE(validate_date, CURRENT_TIMESTAMP) - COALESCE(submit_date, create_date)))/3600) AS validation_duration,
                    AVG(EXTRACT(EPOCH FROM (COALESCE(approve_date, CURRENT_TIMESTAMP) - COALESCE(validate_date, submit_date, create_date)))/3600) AS approval_duration,
                    AVG(EXTRACT(EPOCH FROM (COALESCE(po_create_date, CURRENT_TIMESTAMP) - COALESCE(approve_date, validate_date, submit_date, create_date)))/3600) AS po_creation_duration,
                    AVG(EXTRACT(EPOCH FROM (COALESCE(po_create_date, CURRENT_TIMESTAMP) - create_date))/3600) AS total_duration,
                    COUNT(*) AS count
                FROM
                    purchase_request
                WHERE
                    state = 'po_created'
                GROUP BY
                    to_char(COALESCE(po_create_date, CURRENT_DATE), 'YYYY-MM')
                ORDER BY
                    month DESC
            )
        """ % (self._table,))