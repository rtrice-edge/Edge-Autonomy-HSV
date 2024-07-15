from odoo import models, api

class ReportMOPickList(models.AbstractModel):
    _name = 'report.edge_module.report_mo_pick_list'
    _description = 'MO Pick List Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['mrp.production'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'mrp.production',
            'docs': docs,
            'data': data,
        }