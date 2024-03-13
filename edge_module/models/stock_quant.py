from odoo import models, api

import logging
import json
_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def print_lots_action(self, record_ids):
        lot_ids = self.browse(record_ids).mapped('lot_id.id')
        lots = self.env['stock.lot'].browse(lot_ids)

        lot_data = []
        for lot in lots:
            lot_data.append({
                'product_id': {
                    'display_name': lot.product_id.display_name,
                    'default_code': lot.product_id.default_code,
                    'name': lot.name,
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

        return report_action.report_action(lot_ids, data={
            'options': report_options,
            'docs': lot_data,
        })


        
    
