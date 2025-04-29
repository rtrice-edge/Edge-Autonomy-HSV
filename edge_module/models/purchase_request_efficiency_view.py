from odoo import api, fields, models, tools

class PurchaseRequestEfficiencyView(models.Model):
    _name = 'purchase.request.efficiency.view'
    _description = 'Purchase Request Efficiency Data'
    _auto = False
    
    month = fields.Char(string='Month', readonly=True)
    state = fields.Char(string='State', readonly=True)
    duration_hours = fields.Float(string='Business Hours (8am-5pm)', readonly=True, group_operator="avg", 
                                help="Duration in business hours (8am-5pm, Monday-Friday)")
    count = fields.Integer(string='Number of PRs', readonly=True, group_operator="sum")
    
    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH pr_durations AS (
                    SELECT 
                        id,
                        to_char(COALESCE(po_create_date, CURRENT_DATE), 'YYYY-MM') AS month,
                        -- Duration in each state (in business hours - 8am to 5pm, Monday to Friday)
                        (
                            -- Count business hours between dates (excluding weekends and considering 8am-5pm only)
                            (
                                -- Count business days
                                (EXTRACT(days FROM (COALESCE(submit_date, CURRENT_TIMESTAMP) - create_date)) 
                                - (EXTRACT(week FROM COALESCE(submit_date, CURRENT_TIMESTAMP)) - EXTRACT(week FROM create_date)) * 2  -- Subtract weekends
                                - CASE WHEN EXTRACT(dow FROM create_date) = 0 THEN 1 ELSE 0 END  -- Adjust if start day is Sunday
                                - CASE WHEN EXTRACT(dow FROM create_date) = 6 THEN 1 ELSE 0 END  -- Adjust if start day is Saturday
                                - CASE WHEN EXTRACT(dow FROM COALESCE(submit_date, CURRENT_TIMESTAMP)) = 0 THEN 1 ELSE 0 END  -- Adjust if end day is Sunday
                                - CASE WHEN EXTRACT(dow FROM COALESCE(submit_date, CURRENT_TIMESTAMP)) = 6 THEN 1 ELSE 0 END  -- Adjust if end day is Saturday
                            ) * 9  -- 9 working hours per business day (8am-5pm)
                            
                            -- Adjust for partial days
                            - CASE 
                                -- If start time is within business hours, subtract hours before start
                                WHEN EXTRACT(hour FROM create_date) BETWEEN 8 AND 16 THEN 
                                    EXTRACT(hour FROM create_date) - 8 + EXTRACT(minute FROM create_date)/60.0
                                -- If start time is before business hours, no adjustment needed
                                WHEN EXTRACT(hour FROM create_date) < 8 THEN 0
                                -- If start time is after business hours, subtract full day
                                ELSE 9
                              END
                            - CASE 
                                -- If end time is within business hours, subtract hours after end
                                WHEN EXTRACT(hour FROM COALESCE(submit_date, CURRENT_TIMESTAMP)) BETWEEN 8 AND 16 THEN 
                                    17 - EXTRACT(hour FROM COALESCE(submit_date, CURRENT_TIMESTAMP)) - EXTRACT(minute FROM COALESCE(submit_date, CURRENT_TIMESTAMP))/60.0
                                -- If end time is after business hours, no adjustment needed
                                WHEN EXTRACT(hour FROM COALESCE(submit_date, CURRENT_TIMESTAMP)) >= 17 THEN 0
                                -- If end time is before business hours, subtract full day
                                ELSE 9
                              END
                        ) AS draft_duration,
                        
                        -- Similar calculation for validation time
                        (
                            (EXTRACT(days FROM (COALESCE(validate_date, CURRENT_TIMESTAMP) - COALESCE(submit_date, create_date))) 
                            - (EXTRACT(week FROM COALESCE(validate_date, CURRENT_TIMESTAMP)) - EXTRACT(week FROM COALESCE(submit_date, create_date))) * 2
                            - CASE WHEN EXTRACT(dow FROM COALESCE(submit_date, create_date)) = 0 THEN 1 ELSE 0 END
                            - CASE WHEN EXTRACT(dow FROM COALESCE(submit_date, create_date)) = 6 THEN 1 ELSE 0 END
                            - CASE WHEN EXTRACT(dow FROM COALESCE(validate_date, CURRENT_TIMESTAMP)) = 0 THEN 1 ELSE 0 END
                            - CASE WHEN EXTRACT(dow FROM COALESCE(validate_date, CURRENT_TIMESTAMP)) = 6 THEN 1 ELSE 0 END
                            ) * 9
                            - CASE 
                                WHEN EXTRACT(hour FROM COALESCE(submit_date, create_date)) BETWEEN 8 AND 16 THEN 
                                    EXTRACT(hour FROM COALESCE(submit_date, create_date)) - 8 + EXTRACT(minute FROM COALESCE(submit_date, create_date))/60.0
                                WHEN EXTRACT(hour FROM COALESCE(submit_date, create_date)) < 8 THEN 0
                                ELSE 9
                              END
                            - CASE 
                                WHEN EXTRACT(hour FROM COALESCE(validate_date, CURRENT_TIMESTAMP)) BETWEEN 8 AND 16 THEN 
                                    17 - EXTRACT(hour FROM COALESCE(validate_date, CURRENT_TIMESTAMP)) - EXTRACT(minute FROM COALESCE(validate_date, CURRENT_TIMESTAMP))/60.0
                                WHEN EXTRACT(hour FROM COALESCE(validate_date, CURRENT_TIMESTAMP)) >= 17 THEN 0
                                ELSE 9
                              END
                        AS validation_duration,
                        
                        -- Similar calculation for approval time
                        (
                            (EXTRACT(days FROM (COALESCE(approve_date, CURRENT_TIMESTAMP) - COALESCE(validate_date, submit_date, create_date))) 
                            - (EXTRACT(week FROM COALESCE(approve_date, CURRENT_TIMESTAMP)) - EXTRACT(week FROM COALESCE(validate_date, submit_date, create_date))) * 2
                            - CASE WHEN EXTRACT(dow FROM COALESCE(validate_date, submit_date, create_date)) = 0 THEN 1 ELSE 0 END
                            - CASE WHEN EXTRACT(dow FROM COALESCE(validate_date, submit_date, create_date)) = 6 THEN 1 ELSE 0 END
                            - CASE WHEN EXTRACT(dow FROM COALESCE(approve_date, CURRENT_TIMESTAMP)) = 0 THEN 1 ELSE 0 END
                            - CASE WHEN EXTRACT(dow FROM COALESCE(approve_date, CURRENT_TIMESTAMP)) = 6 THEN 1 ELSE 0 END
                            ) * 9
                            - CASE 
                                WHEN EXTRACT(hour FROM COALESCE(validate_date, submit_date, create_date)) BETWEEN 8 AND 16 THEN 
                                    EXTRACT(hour FROM COALESCE(validate_date, submit_date, create_date)) - 8 + EXTRACT(minute FROM COALESCE(validate_date, submit_date, create_date))/60.0
                                WHEN EXTRACT(hour FROM COALESCE(validate_date, submit_date, create_date)) < 8 THEN 0
                                ELSE 9
                              END
                            - CASE 
                                WHEN EXTRACT(hour FROM COALESCE(approve_date, CURRENT_TIMESTAMP)) BETWEEN 8 AND 16 THEN 
                                    17 - EXTRACT(hour FROM COALESCE(approve_date, CURRENT_TIMESTAMP)) - EXTRACT(minute FROM COALESCE(approve_date, CURRENT_TIMESTAMP))/60.0
                                WHEN EXTRACT(hour FROM COALESCE(approve_date, CURRENT_TIMESTAMP)) >= 17 THEN 0
                                ELSE 9
                              END
                        AS approval_duration,
                        
                        -- Similar calculation for PO creation time
                        (
                            (EXTRACT(days FROM (COALESCE(po_create_date, CURRENT_TIMESTAMP) - COALESCE(approve_date, validate_date, submit_date, create_date))) 
                            - (EXTRACT(week FROM COALESCE(po_create_date, CURRENT_TIMESTAMP)) - EXTRACT(week FROM COALESCE(approve_date, validate_date, submit_date, create_date))) * 2
                            - CASE WHEN EXTRACT(dow FROM COALESCE(approve_date, validate_date, submit_date, create_date)) = 0 THEN 1 ELSE 0 END
                            - CASE WHEN EXTRACT(dow FROM COALESCE(approve_date, validate_date, submit_date, create_date)) = 6 THEN 1 ELSE 0 END
                            - CASE WHEN EXTRACT(dow FROM COALESCE(po_create_date, CURRENT_TIMESTAMP)) = 0 THEN 1 ELSE 0 END
                            - CASE WHEN EXTRACT(dow FROM COALESCE(po_create_date, CURRENT_TIMESTAMP)) = 6 THEN 1 ELSE 0 END
                            ) * 9
                            - CASE 
                                WHEN EXTRACT(hour FROM COALESCE(approve_date, validate_date, submit_date, create_date)) BETWEEN 8 AND 16 THEN 
                                    EXTRACT(hour FROM COALESCE(approve_date, validate_date, submit_date, create_date)) - 8 + EXTRACT(minute FROM COALESCE(approve_date, validate_date, submit_date, create_date))/60.0
                                WHEN EXTRACT(hour FROM COALESCE(approve_date, validate_date, submit_date, create_date)) < 8 THEN 0
                                ELSE 9
                              END
                            - CASE 
                                WHEN EXTRACT(hour FROM COALESCE(po_create_date, CURRENT_TIMESTAMP)) BETWEEN 8 AND 16 THEN 
                                    17 - EXTRACT(hour FROM COALESCE(po_create_date, CURRENT_TIMESTAMP)) - EXTRACT(minute FROM COALESCE(po_create_date, CURRENT_TIMESTAMP))/60.0
                                WHEN EXTRACT(hour FROM COALESCE(po_create_date, CURRENT_TIMESTAMP)) >= 17 THEN 0
                                ELSE 9
                              END
                        AS po_creation_duration
                    FROM 
                        purchase_request
                    WHERE 
                        state = 'po_created'
                )
                -- Unpivot to get one row per state
                SELECT
                    ROW_NUMBER() OVER () as id,
                    month,
                    'Draft' AS state,
                    GREATEST(draft_duration, 0) AS duration_hours,
                    1 AS count
                FROM 
                    pr_durations
                
                UNION ALL
                
                SELECT
                    ROW_NUMBER() OVER () + (SELECT COUNT(*) FROM pr_durations) as id,
                    month,
                    'Pending Validation' AS state,
                    GREATEST(validation_duration, 0) AS duration_hours,
                    1 AS count
                FROM 
                    pr_durations
                
                UNION ALL
                
                SELECT
                    ROW_NUMBER() OVER () + (SELECT COUNT(*) FROM pr_durations) * 2 as id,
                    month,
                    'Pending Approval' AS state,
                    GREATEST(approval_duration, 0) AS duration_hours,
                    1 AS count
                FROM 
                    pr_durations
                
                UNION ALL
                
                SELECT
                    ROW_NUMBER() OVER () + (SELECT COUNT(*) FROM pr_durations) * 3 as id,
                    month,
                    'Awaiting PO Creation' AS state,
                    GREATEST(po_creation_duration, 0) AS duration_hours,
                    1 AS count
                FROM 
                    pr_durations
            )
        """ % (self._table,))