from odoo import models, api

import logging
import json
_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def print_lots_action(self,record_ids):
        lot_data = []
        docids = record_ids
        for quant in self:
            lot_data.append({
                'product_id': {
                    'display_name': quant.product_id.display_name,
                    'default_code': quant.product_id.name,
                    'name': quant.lot_id.name,
                },
            })
            docids.append(quant.id)
        
        report_action = self.env.ref('stock.action_report_lot_label')
        report_options = {
            'report_name': report_action.report_name,
            'report_file': report_action.report_file,
            'report_type': report_action.report_type,
        }
        _logger.info('docs: %s', lot_data)
        _logger.info('options: %s', report_options)
        _logger.info('docids: %s', docids)
        return report_action.report_action(docids,data={
                'options': json.dumps(report_options),
                'docs': json.dumps(lot_data),
            },docs=lot_data)

        
    
