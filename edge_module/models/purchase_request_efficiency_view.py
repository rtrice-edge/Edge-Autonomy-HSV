from odoo import api, fields, models, tools

class PurchaseRequestEfficiencyView(models.Model):
    _name = 'purchase.request.efficiency.view'
    _description = 'Purchase Request Efficiency Data'
    _auto = False
    
    month = fields.Char(string='Month', readonly=True)
    state = fields.Char(string='State', readonly=True)
    duration_hours = fields.Float(string='Business Hours (PST 8am-5pm)', readonly=True, group_operator="avg", 
                                help="Duration in business hours (PST 8am-5pm, Monday-Friday)")
    count = fields.Integer(string='Number of PRs', readonly=True, group_operator="sum")
    
    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH pr_durations AS (
                    SELECT 
                        id,
                        to_char(COALESCE(po_create_date, CURRENT_DATE), 'YYYY-MM') AS month,
                        
                        -- Calculate business hours for draft state
                        -- Adjust timestamps to PST (subtract 9 hours from DB timestamps)
                        GREATEST(
                            (
                                -- Count business days between dates
                                EXTRACT(days FROM ((COALESCE(submit_date, CURRENT_TIMESTAMP) - interval '9 hours') - (create_date - interval '9 hours'))) 
                                -- Subtract weekends
                                - (EXTRACT(week FROM (COALESCE(submit_date, CURRENT_TIMESTAMP) - interval '9 hours')) - EXTRACT(week FROM (create_date - interval '9 hours'))) * 2
                                -- Adjust if start day is Sunday (in PST)
                                - CASE WHEN EXTRACT(dow FROM (create_date - interval '9 hours')) = 0 THEN 1 ELSE 0 END
                                -- Adjust if start day is Saturday (in PST)
                                - CASE WHEN EXTRACT(dow FROM (create_date - interval '9 hours')) = 6 THEN 1 ELSE 0 END
                                -- Adjust if end day is Sunday (in PST)
                                - CASE WHEN EXTRACT(dow FROM (COALESCE(submit_date, CURRENT_TIMESTAMP) - interval '9 hours')) = 0 THEN 1 ELSE 0 END
                                -- Adjust if end day is Saturday (in PST)
                                - CASE WHEN EXTRACT(dow FROM (COALESCE(submit_date, CURRENT_TIMESTAMP) - interval '9 hours')) = 6 THEN 1 ELSE 0 END
                            ) * 9  -- 9 working hours per business day (8am-5pm)
                            
                            -- Adjust for partial days
                            - CASE 
                                -- If start time is within business hours, subtract hours before start (in PST)
                                WHEN EXTRACT(hour FROM (create_date - interval '9 hours')) BETWEEN 8 AND 16 THEN 
                                    EXTRACT(hour FROM (create_date - interval '9 hours')) - 8 + EXTRACT(minute FROM (create_date - interval '9 hours'))/60.0
                                -- If start time is before business hours, no adjustment needed
                                WHEN EXTRACT(hour FROM (create_date - interval '9 hours')) < 8 THEN 0
                                -- If start time is after business hours, subtract full day
                                ELSE 9
                              END
                            - CASE 
                                -- If end time is within business hours, subtract hours after end (in PST)
                                WHEN EXTRACT(hour FROM (COALESCE(submit_date, CURRENT_TIMESTAMP) - interval '9 hours')) BETWEEN 8 AND 16 THEN 
                                    17 - EXTRACT(hour FROM (COALESCE(submit_date, CURRENT_TIMESTAMP) - interval '9 hours')) - EXTRACT(minute FROM (COALESCE(submit_date, CURRENT_TIMESTAMP) - interval '9 hours'))/60.0
                                -- If end time is after business hours, no adjustment needed
                                WHEN EXTRACT(hour FROM (COALESCE(submit_date, CURRENT_TIMESTAMP) - interval '9 hours')) >= 17 THEN 0
                                -- If end time is before business hours, subtract full day
                                ELSE 9
                              END,
                            0
                        ) AS draft_duration,
                        
                        -- Calculate business hours for validation state
                        GREATEST(
                            (
                                -- Count business days with PST adjustment
                                EXTRACT(days FROM ((COALESCE(validate_date, CURRENT_TIMESTAMP) - interval '9 hours') - (COALESCE(submit_date, create_date) - interval '9 hours'))) 
                                - (EXTRACT(week FROM (COALESCE(validate_date, CURRENT_TIMESTAMP) - interval '9 hours')) - EXTRACT(week FROM (COALESCE(submit_date, create_date) - interval '9 hours'))) * 2
                                - CASE WHEN EXTRACT(dow FROM (COALESCE(submit_date, create_date) - interval '9 hours')) = 0 THEN 1 ELSE 0 END
                                - CASE WHEN EXTRACT(dow FROM (COALESCE(submit_date, create_date) - interval '9 hours')) = 6 THEN 1 ELSE 0 END
                                - CASE WHEN EXTRACT(dow FROM (COALESCE(validate_date, CURRENT_TIMESTAMP) - interval '9 hours')) = 0 THEN 1 ELSE 0 END
                                - CASE WHEN EXTRACT(dow FROM (COALESCE(validate_date, CURRENT_TIMESTAMP) - interval '9 hours')) = 6 THEN 1 ELSE 0 END
                            ) * 9
                            - CASE 
                                WHEN EXTRACT(hour FROM (COALESCE(submit_date, create_date) - interval '9 hours')) BETWEEN 8 AND 16 THEN 
                                    EXTRACT(hour FROM (COALESCE(submit_date, create_date) - interval '9 hours')) - 8 + EXTRACT(minute FROM (COALESCE(submit_date, create_date) - interval '9 hours'))/60.0
                                WHEN EXTRACT(hour FROM (COALESCE(submit_date, create_date) - interval '9 hours')) < 8 THEN 0
                                ELSE 9
                              END
                            - CASE 
                                WHEN EXTRACT(hour FROM (COALESCE(validate_date, CURRENT_TIMESTAMP) - interval '9 hours')) BETWEEN 8 AND 16 THEN 
                                    17 - EXTRACT(hour FROM (COALESCE(validate_date, CURRENT_TIMESTAMP) - interval '9 hours')) - EXTRACT(minute FROM (COALESCE(validate_date, CURRENT_TIMESTAMP) - interval '9 hours'))/60.0
                                WHEN EXTRACT(hour FROM (COALESCE(validate_date, CURRENT_TIMESTAMP) - interval '9 hours')) >= 17 THEN 0
                                ELSE 9
                              END,
                            0
                        ) AS validation_duration,
                        
                        -- Calculate business hours for approval state with PST adjustment
                        GREATEST(
                            (
                                EXTRACT(days FROM ((COALESCE(approve_date, CURRENT_TIMESTAMP) - interval '9 hours') - (COALESCE(validate_date, submit_date, create_date) - interval '9 hours'))) 
                                - (EXTRACT(week FROM (COALESCE(approve_date, CURRENT_TIMESTAMP) - interval '9 hours')) - EXTRACT(week FROM (COALESCE(validate_date, submit_date, create_date) - interval '9 hours'))) * 2
                                - CASE WHEN EXTRACT(dow FROM (COALESCE(validate_date, submit_date, create_date) - interval '9 hours')) = 0 THEN 1 ELSE 0 END
                                - CASE WHEN EXTRACT(dow FROM (COALESCE(validate_date, submit_date, create_date) - interval '9 hours')) = 6 THEN 1 ELSE 0 END
                                - CASE WHEN EXTRACT(dow FROM (COALESCE(approve_date, CURRENT_TIMESTAMP) - interval '9 hours')) = 0 THEN 1 ELSE 0 END
                                - CASE WHEN EXTRACT(dow FROM (COALESCE(approve_date, CURRENT_TIMESTAMP) - interval '9 hours')) = 6 THEN 1 ELSE 0 END
                            ) * 9
                            - CASE 
                                WHEN EXTRACT(hour FROM (COALESCE(validate_date, submit_date, create_date) - interval '9 hours')) BETWEEN 8 AND 16 THEN 
                                    EXTRACT(hour FROM (COALESCE(validate_date, submit_date, create_date) - interval '9 hours')) - 8 + EXTRACT(minute FROM (COALESCE(validate_date, submit_date, create_date) - interval '9 hours'))/60.0
                                WHEN EXTRACT(hour FROM (COALESCE(validate_date, submit_date, create_date) - interval '9 hours')) < 8 THEN 0
                                ELSE 9
                              END
                            - CASE 
                                WHEN EXTRACT(hour FROM (COALESCE(approve_date, CURRENT_TIMESTAMP) - interval '9 hours')) BETWEEN 8 AND 16 THEN 
                                    17 - EXTRACT(hour FROM (COALESCE(approve_date, CURRENT_TIMESTAMP) - interval '9 hours')) - EXTRACT(minute FROM (COALESCE(approve_date, CURRENT_TIMESTAMP) - interval '9 hours'))/60.0
                                WHEN EXTRACT(hour FROM (COALESCE(approve_date, CURRENT_TIMESTAMP) - interval '9 hours')) >= 17 THEN 0
                                ELSE 9
                              END,
                            0
                        ) AS approval_duration,
                        
                        -- Calculate business hours for PO creation state with PST adjustment
                        GREATEST(
                            (
                                EXTRACT(days FROM ((COALESCE(po_create_date, CURRENT_TIMESTAMP) - interval '9 hours') - (COALESCE(approve_date, validate_date, submit_date, create_date) - interval '9 hours'))) 
                                - (EXTRACT(week FROM (COALESCE(po_create_date, CURRENT_TIMESTAMP) - interval '9 hours')) - EXTRACT(week FROM (COALESCE(approve_date, validate_date, submit_date, create_date) - interval '9 hours'))) * 2
                                - CASE WHEN EXTRACT(dow FROM (COALESCE(approve_date, validate_date, submit_date, create_date) - interval '9 hours')) = 0 THEN 1 ELSE 0 END
                                - CASE WHEN EXTRACT(dow FROM (COALESCE(approve_date, validate_date, submit_date, create_date) - interval '9 hours')) = 6 THEN 1 ELSE 0 END
                                - CASE WHEN EXTRACT(dow FROM (COALESCE(po_create_date, CURRENT_TIMESTAMP) - interval '9 hours')) = 0 THEN 1 ELSE 0 END
                                - CASE WHEN EXTRACT(dow FROM (COALESCE(po_create_date, CURRENT_TIMESTAMP) - interval '9 hours')) = 6 THEN 1 ELSE 0 END
                            ) * 9
                            - CASE 
                                WHEN EXTRACT(hour FROM (COALESCE(approve_date, validate_date, submit_date, create_date) - interval '9 hours')) BETWEEN 8 AND 16 THEN 
                                    EXTRACT(hour FROM (COALESCE(approve_date, validate_date, submit_date, create_date) - interval '9 hours')) - 8 + EXTRACT(minute FROM (COALESCE(approve_date, validate_date, submit_date, create_date) - interval '9 hours'))/60.0
                                WHEN EXTRACT(hour FROM (COALESCE(approve_date, validate_date, submit_date, create_date) - interval '9 hours')) < 8 THEN 0
                                ELSE 9
                              END
                            - CASE 
                                WHEN EXTRACT(hour FROM (COALESCE(po_create_date, CURRENT_TIMESTAMP) - interval '9 hours')) BETWEEN 8 AND 16 THEN 
                                    17 - EXTRACT(hour FROM (COALESCE(po_create_date, CURRENT_TIMESTAMP) - interval '9 hours')) - EXTRACT(minute FROM (COALESCE(po_create_date, CURRENT_TIMESTAMP) - interval '9 hours'))/60.0
                                WHEN EXTRACT(hour FROM (COALESCE(po_create_date, CURRENT_TIMESTAMP) - interval '9 hours')) >= 17 THEN 0
                                ELSE 9
                              END,
                            0
                        ) AS po_creation_duration
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
                    draft_duration AS duration_hours,
                    1 AS count
                FROM 
                    pr_durations
                
                UNION ALL
                
                SELECT
                    ROW_NUMBER() OVER () + (SELECT COUNT(*) FROM pr_durations) as id,
                    month,
                    'Pending Validation' AS state,
                    validation_duration AS duration_hours,
                    1 AS count
                FROM 
                    pr_durations
                
                UNION ALL
                
                SELECT
                    ROW_NUMBER() OVER () + (SELECT COUNT(*) FROM pr_durations) * 2 as id,
                    month,
                    'Pending Approval' AS state,
                    approval_duration AS duration_hours,
                    1 AS count
                FROM 
                    pr_durations
                
                UNION ALL
                
                SELECT
                    ROW_NUMBER() OVER () + (SELECT COUNT(*) FROM pr_durations) * 3 as id,
                    month,
                    'Awaiting PO Creation' AS state,
                    po_creation_duration AS duration_hours,
                    1 AS count
                FROM 
                    pr_durations
            )
        """ % (self._table,))