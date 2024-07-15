from odoo import models, api

class ReportMOPickList(models.AbstractModel):
    _name = 'report.edge_module.report_mo_pick_list'
    _description = 'MO Pick List Report'

    @api.model
    def _get_available_locations(self, move):
        return self.env['stock.quant'].search([
            ('product_id', '=', move.product_id.id),
            ('location_id.usage', '=', 'internal'),
            ('quantity', '>', 0),
            ('reserved_quantity', '<', 'quantity')
        ]).mapped('location_id')

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['mrp.production'].browse(docids)

        return {
            'doc_ids': docids,
            'doc_model': 'mrp.production',
            'docs': docs,
            'data': data,
            'get_available_locations': self._get_available_locations,
        }