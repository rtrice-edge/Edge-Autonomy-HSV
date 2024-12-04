from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class ReportMrpOrderComponents(models.AbstractModel):
    _name = 'report.edge_module.report_mrp_order_components'
    _description = 'MO Components Report'

    def _prepare_production_data(self, production):
        try:
            data = {
                'id': production.id,
                'name': production.name,
                'product_id': production.product_id,
                'product_tmpl_id': production.product_id.product_tmpl_id if production.product_id else None,
                'lot_producing_id': production.lot_producing_id,
                'product_qty': production.product_qty,
                'qty_producing': production.qty_producing,
                'product_uom_id': production.product_uom_id,
                'date_start': production.date_start,
                'date_finished': production.date_finished,
                'bom_id': production.bom_id,
                'move_raw_ids': [(move, move.product_id.type) for move in production.move_raw_ids],  # Include product type
            }
            return data
        except Exception as e:
            _logger.error(f"Error preparing production data for MO {production.name}: {str(e)}")
            return {'name': production.name, 'error': str(e)}

    def _get_sub_mos(self, production, processed_mos=None):
        if processed_mos is None:
            processed_mos = set()

        sub_mos = []
        for move in production.move_raw_ids:
            if move.lot_ids:
                for lot in move.lot_ids:
                    producing_mo = self.env['mrp.production'].search([
                        ('lot_producing_id', '=', lot.id),
                        ('product_id', '=', move.product_id.id)
                    ], limit=1)
                    
                    if producing_mo and producing_mo.id not in processed_mos:
                        if producing_mo.product_id.categ_id.name.lower() != 'manufactured wire':
                            processed_mos.add(producing_mo.id)
                            sub_mo_data = self._prepare_production_data(producing_mo)
                            sub_mo_data['sub_mos'] = self._get_sub_mos(producing_mo, processed_mos)
                            sub_mos.append(sub_mo_data)

        return sub_mos

    @api.model
    def _get_report_values(self, docids, data=None):
        _logger.info(f"Generating components report for docids: {docids}")
        docs = self.env['mrp.production'].browse(docids)
        processed_docs = []
        
        for doc in docs:
            _logger.info(f"Processing document: {doc.name}")
            try:
                production_data = self._prepare_production_data(doc)
                production_data['sub_mos'] = self._get_sub_mos(doc)
                processed_doc = {
                    'production': production_data,
                    'o': doc,
                }
                processed_docs.append(processed_doc)
            except Exception as e:
                _logger.error(f"Error processing document {doc.name}: {str(e)}")
                processed_docs.append({
                    'production': {'name': doc.name, 'error': str(e)},
                    'o': doc,
                })

        return {
            'doc_ids': docids,
            'doc_model': 'mrp.production',
            'docs': processed_docs,
        }