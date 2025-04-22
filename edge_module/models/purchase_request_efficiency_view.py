from odoo import api, fields, models, tools

class PurchaseRequestEfficiencyView(models.Model):
    _name = 'purchase.request.efficiency.view'
    _description = 'Purchase Request Efficiency Data'
    _auto = False
    
    month = fields.Char(string='Month', readonly=True)
    state = fields.Char(string='State', readonly=True)
    duration_hours = fields.Float(string='Duration (hrs)', readonly=True, group_operator="avg")
    count = fields.Integer(string='Number of PRs', readonly=True, group_operator="sum")
    
    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH pr_durations AS (
                    SELECT 
                        id,
                        to_char(COALESCE(po_create_date, CURRENT_DATE), 'YYYY-MM') AS month,
                        -- Duration in each state (in hours)
                        EXTRACT(EPOCH FROM (COALESCE(submit_date, CURRENT_TIMESTAMP) - create_date))/3600 AS draft_duration,
                        EXTRACT(EPOCH FROM (COALESCE(validate_date, CURRENT_TIMESTAMP) - COALESCE(submit_date, create_date)))/3600 AS validation_duration,
                        EXTRACT(EPOCH FROM (COALESCE(approve_date, CURRENT_TIMESTAMP) - COALESCE(validate_date, submit_date, create_date)))/3600 AS approval_duration,
                        EXTRACT(EPOCH FROM (COALESCE(po_create_date, CURRENT_TIMESTAMP) - COALESCE(approve_date, validate_date, submit_date, create_date)))/3600 AS po_creation_duration
                    FROM 
                        purchase_request
                    WHERE 
                        state = 'po_created'
                )
                -- Unpivot to get one row per state
                SELECT
                    ROW_NUMBER() OVER () as id,
                    month,
                    'Step 1: In Draft State' AS state,
                    draft_duration AS duration_hours,
                    1 AS count
                FROM 
                    pr_durations
                
                UNION ALL
                
                SELECT
                    ROW_NUMBER() OVER () + (SELECT COUNT(*) FROM pr_durations) as id,
                    month,
                    'Step 2: Pending Validation' AS state,
                    validation_duration AS duration_hours,
                    1 AS count
                FROM 
                    pr_durations
                
                UNION ALL
                
                SELECT
                    ROW_NUMBER() OVER () + (SELECT COUNT(*) FROM pr_durations) * 2 as id,
                    month,
                    'Step 3: Pending Approval' AS state,
                    approval_duration AS duration_hours,
                    1 AS count
                FROM 
                    pr_durations
                
                UNION ALL
                
                SELECT
                    ROW_NUMBER() OVER () + (SELECT COUNT(*) FROM pr_durations) * 3 as id,
                    month,
                    'Step 4: Awaiting PO Creation' AS state,
                    po_creation_duration AS duration_hours,
                    1 AS count
                FROM 
                    pr_durations
            )
        """ % (self._table,))