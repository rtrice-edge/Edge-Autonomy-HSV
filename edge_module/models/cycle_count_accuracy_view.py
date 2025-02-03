# models/cycle_count_accuracy_view.py
from odoo import models, fields, tools

class CycleCountAccuracyView(models.Model):
    _name = 'inventory.cycle.count.accuracy.view'
    _description = 'Cycle Count Accuracy Data'
    _auto = False

    # We are grouping by month and product category.
    month = fields.Char(string='Cycle Count Month', readonly=True)
    category = fields.Char(string='Category', readonly=True)
    total_logs = fields.Integer(string='Total Logs', readonly=True)
    correct_logs = fields.Integer(string='Correct Logs', readonly=True)
    accuracy = fields.Float(string='Accuracy (%)', readonly=True)

    def init(self):
        # Drop the view if it exists and create a new one.
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    MIN(l.id) as id,
                    to_char(l.planned_count_date, 'YYYY-MM') as month,
                    p.product_inventory_category as category,
                    COUNT(*) as total_logs,
                    SUM(CASE WHEN l.difference = 0 THEN 1 ELSE 0 END) as correct_logs,
                    ROUND( (SUM(CASE WHEN l.difference = 0 THEN 1 ELSE 0 END)::numeric / COUNT(*) * 100), 2) as accuracy
                FROM inventory_cycle_count_log l
                JOIN product_product p on l.product_id = p.id
                WHERE l.planned_count_date >= date_trunc('month', now()) - interval '10 months'
                GROUP BY to_char(l.planned_count_date, 'YYYY-MM'), p.product_inventory_category
                ORDER BY to_char(l.planned_count_date, 'YYYY-MM') DESC, p.product_inventory_category
            )
        """ % (self._table,))
