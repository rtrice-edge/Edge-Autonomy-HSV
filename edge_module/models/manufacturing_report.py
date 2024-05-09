from odoo import models, fields, api

class ManufacturingOrder(models.Model):
    _inherit = 'manufacturing.order'

    @api.multi
    def action_custom_report(self):
        self.ensure_one()  # Ensure only one record is selected

        report_service = self.env.ref('your_module.report_custom_manufacturing_order')
        return report_service.report_action(self)

    def _html_report_content(self, report=None, docargs=None):
        # If needed, modify or add custom logic for report generation
        docargs = {'doc_ids': self.ids, 'doc_model': self._name}
        return self.env.ref('your_module.custom_manufacturing_order_report').render(docargs)