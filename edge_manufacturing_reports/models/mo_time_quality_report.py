# mo_time_quality_report/models/mo_time_quality_report.py
from odoo import models, fields, tools

class MoTimeQualityReport(models.Model):
    _name = 'mo.time.quality.report'
    _description = 'MO Time & Quality Check Report'
    _auto = False

    product_code       = fields.Char(string='Product Code', readonly=True)
    product_name       = fields.Char(string='Product Name', readonly=True)
    department         = fields.Char(string='Department', readonly=True)
    operation_step     = fields.Char(string='Operation Step', readonly=True)
    employee           = fields.Char(string='Employee', readonly=True)
    has_quality_check  = fields.Selection([('Yes','Yes'),('No','No')], string='Has QC Point', readonly=True)
    total_time_h       = fields.Float(string='Total Time (h)', readonly=True)
    total_mos          = fields.Integer(string='Total MOs', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'mo_time_quality_report')
        self.env.cr.execute("""
        CREATE OR REPLACE VIEW mo_time_quality_report AS (
          SELECT
            MIN(prod.id)                                         AS id,
            pp.default_code                                      AS product_code,
            (pt.name::json ->> 'en_US')                          AS product_name,
            (dept.name::json ->> 'en_US')                        AS department,
            op.name                                              AS operation_step,
            emp.name                                             AS employee,
            CASE WHEN COUNT(DISTINCT qrel.quality_point_id) > 0
                 THEN 'Yes' ELSE 'No' END                       AS has_quality_check,
            ROUND(SUM(prod.duration)::numeric, 2)                 AS total_time_h,
            COUNT(DISTINCT wo.production_id)                      AS total_mos
          FROM mrp_workorder wo
          JOIN mrp_production                 mp   ON wo.production_id    = mp.id
          JOIN product_product                pp   ON mp.product_id       = pp.id
          JOIN product_template               pt   ON pp.product_tmpl_id  = pt.id
          JOIN mrp_workcenter_productivity    prod ON prod.workorder_id   = wo.id
                                                AND prod.loss_type     = 'productive'
          JOIN mrp_routing_workcenter         op   ON wo.operation_id     = op.id
          JOIN hr_employee                    emp  ON prod.user_id        = emp.user_id
          JOIN hr_department                  dept ON emp.department_id   = dept.id
          LEFT JOIN mrp_workorder_quality_point_rel qrel
                                                ON qrel.mrp_workorder_id = wo.id
          WHERE (dept.name::json ->> 'en_US') IN ('Electronics','Quality')
          GROUP BY
            pp.default_code,
            (pt.name::json ->> 'en_US'),
            (dept.name::json ->> 'en_US'),
            op.name,
            emp.name
        )
        """)
