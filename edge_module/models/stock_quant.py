from odoo import models, api

import logging
import json
_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def print_lots_action(self):
        lot_data = []
        for quant in self:
            lot_data.append({
                'product_id': {
                    'display_name': quant.product_id.display_name,
                    'default_code': quant.product_id.name,
                    'name': quant.lot_id.name,
                },
            })
        
        report_action = self.env.ref('stock.action_report_lot_label')
        report_options = {
            'report_name': report_action.report_name,
            'report_file': report_action.report_file,
            'report_type': report_action.report_type,
        }
        _logger.info('docs: %s', lot_data)
        _logger.info('options: %s', report_options)
        return {
            'type': 'ir.actions.report',
            'report_name': report_action.report_name,
            'report_type': report_action.report_type,
            'data': {
                'options': json.dumps(report_options),
                'docs': lot_data,
            },
        }
    
