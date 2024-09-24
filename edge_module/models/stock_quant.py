from odoo import models, api, fields

import logging
import json
_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _inherit = 'stock.quant'
    def action_apply_inventory(self):
        res = super(StockQuant, self).action_apply_inventory()
        
        CycleCountLog = self.env['inventory.cycle.count.log']
        CycleCount = self.env['inventory.cycle.count']
        
        for quant in self:
            # Find the cycle count with matching inventory_date
            cycle_count = CycleCount.search([
                ('date', '=', quant.inventory_date),
                ('state', '=', 'in_progress')
            ], limit=1)
            
            if cycle_count:
                # Create cycle count log entry
                CycleCountLog.create({
                    'cycle_count_id': cycle_count.id,
                    'product_id': quant.product_id.id,
                    'expected_quantity': quant.inventory_quantity_auto,
                    'actual_quantity': quant.inventory_quantity,
                    'actual_count_date': fields.Datetime.now(),
                    'user_id': self.env.user.id,
                })
                
                # Check if all stock quants for this cycle count have been processed
                remaining_quants = self.search([
                    ('inventory_date', '=', cycle_count.date),
                    ('inventory_quantity', '=', False)  # Uncounted quants
                ])
                
                if not remaining_quants:
                    # All quants have been counted, set cycle count to 'done'
                    cycle_count.write({'state': 'done'})
        
        return res
    
    def print_lots_action(self, record_ids):
        lot_ids = self.browse(record_ids).mapped('lot_id.id')
        lots = self.env['stock.lot'].browse(lot_ids)

        # lot_data = []
        # for lot in lots:
        #     lot_data.append({
        #         'product_id': {
        #             'display_name': lot.product_id.display_name,
        #             'default_code': lot.product_id.default_code,
        #             'name': lot.name,
        #         },
        #     })

        report_action = self.env.ref('stock.action_report_lot_label')
        report_options = {
            'report_name': report_action.report_name,
            'report_file': report_action.report_file,
            'report_type': report_action.report_type,
        }

        _logger.info('docs: %s', lots)
        _logger.info('docs: %s', lot_ids)
        _logger.info('options: %s', report_options)

        return report_action.report_action(lot_ids, config=False)


        
    
