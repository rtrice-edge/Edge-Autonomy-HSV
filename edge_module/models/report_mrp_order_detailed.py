from odoo import models, fields, api

class ReportMrpOrderDetailed(models.AbstractModel):
    _name = 'report.your_module.report_mrp_order_detailed'
    _description = 'Detailed MO Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['mrp.production'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'mrp.production',
            'docs': docs,
            'get_worker_times': lambda doc: doc.get_worker_times(),
            'get_initials': lambda doc, name: doc.get_initials(name),
        }