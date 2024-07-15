from odoo import api, models

class ReportMOPickList(models.AbstractModel):
    _name = 'report.edge_module.report_mo_pick_list'
    _description = 'MO Pick List Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['mrp.production'].browse(docids)
        
        def get_available_locations(move):
            locations = self.env['stock.quant'].search([
                ('product_id', '=', move.product_id.id),
                ('location_id.usage', '=', 'internal'),
                ('quantity', '>', 0),
                ('reserved_quantity', '<', 'quantity')
            ]).mapped('location_id')
            return locations

        for doc in docs:
            for move in doc.move_raw_ids:
                move.available_locations = get_available_locations(move)

        return {
            'doc_ids': docids,
            'doc_model': 'mrp.production',
            'docs': docs,
            'data': data,
        }