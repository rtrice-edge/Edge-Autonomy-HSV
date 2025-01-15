from odoo import models, fields, api
from datetime import datetime, timedelta

class KitDashboard(models.Model):
    _name = 'kit.dashboard'
    _description = 'Kit Production Dashboard'
    _auto = False  # This model does not create a database table

    kit_code = fields.Char(string="Kit Code")
    months = fields.Char(string="Months")
    total_kits = fields.Integer(string="Total Kits")
    total_parts = fields.Integer(string="Total Parts")

    @api.model
    def get_dashboard_data(self):
        months = self._get_last_12_months()
        mo_model = self.env['mrp.production']
        data = []

        for kit in self._get_kits_with_productions():
            row = {"kit_code": kit}
            for month in months:
                start_date = datetime.strptime(month, '%B %Y').replace(day=1)
                end_date = (start_date + timedelta(days=31)).replace(day=1) - timedelta(days=1)

                mos = mo_model.search([
                    ('date_planned_start', '>=', start_date),
                    ('date_planned_start', '<=', end_date),
                    ('product_id.default_code', '=', kit)
                ])
                total_kits = sum(mo.qty_produced for mo in mos)
                total_parts = sum(
                    sum(move.product_uom_qty * mo.qty_produced for move in mo.move_raw_ids)
                    for mo in mos
                )
                row[month] = f"{total_kits} ({total_parts})"
            data.append(row)

        return {"months": months, "data": data}

    def _get_last_12_months(self):
        today = datetime.today()
        return [(today - timedelta(days=30 * i)).strftime('%B %Y') for i in range(11, -1, -1)]

    def _get_kits_with_productions(self):
        """Retrieve all unique KIT codes with '-KIT'."""
        mo_model = self.env['mrp.production']
        mos = mo_model.search([('product_id.default_code', '=like', '%-KIT')])
        return list(set(mo.product_id.default_code for mo in mos))
