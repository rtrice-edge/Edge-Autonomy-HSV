# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import datetime

class StockHistoryReportWizard(models.TransientModel):
    _name = 'stock.history.report.wizard'
    _description = 'Stock History Snapshot Report Wizard'

    date_snapshot = fields.Date(
        string="Inventory Snapshot Date",
        required=True,
        default=fields.Date.today,
        help="Select the date for which you want to see the inventory levels.")

    def generate_report(self):
        self.ensure_one()
        # Prepare data for the report action
        data = {'date_snapshot': self.date_snapshot}
        return self.env.ref('your_module_name.action_report_inventory_snapshot').report_action(self, data=data)
        # Replace 'your_module_name' with the actual name of your custom module