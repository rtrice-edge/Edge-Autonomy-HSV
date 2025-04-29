from odoo import api, fields, models, tools

class PurchaseRequestEfficiencyReport(models.Model):
    _name = 'purchase.request.efficiency.report'
    _description = 'Purchase Request Efficiency Report'
    _auto = False
    _rec_name = 'month'
    
    month = fields.Char(string='Month', readonly=True)
    draft_duration = fields.Float(string='Draft (Business Hrs)', readonly=True, group_operator="avg",
                                help="Average business hours (8am-5pm, Mon-Fri) spent in Draft state")
    validation_duration = fields.Float(string='Validation (Business Hrs)', readonly=True, group_operator="avg",
                                    help="Average business hours (8am-5pm, Mon-Fri) spent in Pending Validation state")
    approval_duration = fields.Float(string='Approval (Business Hrs)', readonly=True, group_operator="avg",
                                   help="Average business hours (8am-5pm, Mon-Fri) spent in Pending Approval state")
    po_creation_duration = fields.Float(string='PO Creation (Business Hrs)', readonly=True, group_operator="avg",
                                      help="Average business hours (8am-5pm, Mon-Fri) spent in Awaiting PO Creation state")
    total_duration = fields.Float(string='Total (Business Hrs)', readonly=True, group_operator="avg",
                                help="Average total business hours (8am-5pm, Mon-Fri) from creation to PO creation")
    count = fields.Integer(string='Number of PRs', readonly=True, group_operator="sum")
    
    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH pr_durations AS (
                    SELECT 
                        id,
                        to_char(COALESCE(po_create_date, CURRENT_DATE), 'YYYY-MM') AS month,
                        
                        -- Calculate business hours for various stages using the same logic as the detailed view
                        -- Draft duration
                        GREATEST(
                            (EXTRACT(days FROM (COALESCE(submit_date, CURRENT_TIMESTAMP) - create_date)) 
                            - (EXTRACT(week FROM COALESCE(submit_date, CURRENT_TIMESTAMP)) - EXTRACT(week FROM create_date)) * 2
                            - CASE WHEN EXTRACT(dow FROM create_date) = 0 THEN 1 ELSE 0 END
                            - CASE WHEN EXTRACT(dow FROM create_date) = 6 THEN 1 ELSE 0 END
                            - CASE WHEN EXTRACT(dow FROM COALESCE(submit_date, CURRENT_TIMESTAMP)) = 0 THEN 1 ELSE 0 END
                            - CASE WHEN EXTRACT(dow FROM COALESCE(submit_date, CURRENT_TIMESTAMP)) = 6 THEN 1 ELSE 0 END
                            ) * 9
                            - CASE 
                                WHEN EXTRACT(hour FROM create_date) BETWEEN 8 AND 16 THEN 
                                    EXTRACT(hour FROM create_date) - 8 + EXTRACT(minute FROM create_date)/60.0
                                WHEN EXTRACT(hour FROM create_date) < 8 THEN 0
                                ELSE 9
                              END
                            - CASE 
                                WHEN EXTRACT(hour FROM COALESCE(submit_date, CURRENT_TIMESTAMP)) BETWEEN 8 AND 16 THEN 
                                    17 - EXTRACT(hour FROM COALESCE(submit_date, CURRENT_TIMESTAMP)) - EXTRACT(minute FROM COALESCE(submit_date, CURRENT_TIMESTAMP))/60.0
                                WHEN EXTRACT(hour FROM COALESCE(submit_date, CURRENT_TIMESTAMP)) >= 17 THEN 0
                                ELSE 9
                              END,
                            0
                        ) AS draft_duration,
                        
                        -- Validation duration
                        GREATEST(
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
                              END,
                            0
                        ) AS validation_duration,
                        
                        -- Approval duration
                        GREATEST(
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
                              END,
                            0
                        ) AS approval_duration,
                        
                        -- PO creation duration
                        GREATEST(
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
                              END,
                            0
                        ) AS po_creation_duration,
                        
                        -- Total duration from creation to PO creation
                        GREATEST(
                            (EXTRACT(days FROM (COALESCE(po_create_date, CURRENT_TIMESTAMP) - create_date)) 
                            - (EXTRACT(week FROM COALESCE(po_create_date, CURRENT_TIMESTAMP)) - EXTRACT(week FROM create_date)) * 2
                            - CASE WHEN EXTRACT(dow FROM create_date) = 0 THEN 1 ELSE 0 END
                            - CASE WHEN EXTRACT(dow FROM create_date) = 6 THEN 1 ELSE 0 END
                            - CASE WHEN EXTRACT(dow FROM COALESCE(po_create_date, CURRENT_TIMESTAMP)) = 0 THEN 1 ELSE 0 END
                            - CASE WHEN EXTRACT(dow FROM COALESCE(po_create_date, CURRENT_TIMESTAMP)) = 6 THEN 1 ELSE 0 END
                            ) * 9
                            - CASE 
                                WHEN EXTRACT(hour FROM create_date) BETWEEN 8 AND 16 THEN 
                                    EXTRACT(hour FROM create_date) - 8 + EXTRACT(minute FROM create_date)/60.0
                                WHEN EXTRACT(hour FROM create_date) < 8 THEN 0
                                ELSE 9
                              END
                            - CASE 
                                WHEN EXTRACT(hour FROM COALESCE(po_create_date, CURRENT_TIMESTAMP)) BETWEEN 8 AND 16 THEN 
                                    17 - EXTRACT(hour FROM COALESCE(po_create_date, CURRENT_TIMESTAMP)) - EXTRACT(minute FROM COALESCE(po_create_date, CURRENT_TIMESTAMP))/60.0
                                WHEN EXTRACT(hour FROM COALESCE(po_create_date, CURRENT_TIMESTAMP)) >= 17 THEN 0
                                ELSE 9
                              END,
                            0
                        ) AS total_duration
                    FROM 
                        purchase_request
                    WHERE 
                        state = 'po_created'
                )
                
                -- Aggregate data by month
                SELECT
                    MIN(id) as id,
                    month,
                    AVG(draft_duration) AS draft_duration,
                    AVG(validation_duration) AS validation_duration,
                    AVG(approval_duration) AS approval_duration,
                    AVG(po_creation_duration) AS po_creation_duration,
                    AVG(total_duration) AS total_duration,
                    COUNT(*) AS count
                FROM
                    pr_durations
                GROUP BY
                    month
                ORDER BY
                    month DESC
            )
        """ % (self._table,))