from odoo import models, api, fields

import logging
import json
_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _inherit = 'stock.quant'
    
    product_inventory_category = fields.Selection(
        related='product_id.product_tmpl_id.product_inventory_category',
        string='Inventory Category',
        store=True,  # This allows grouping and searching
    )

    def _get_inventory_category_color(self):
        colors = {'A': 'success', 'B': 'warning', 'C': 'danger'}
        return colors.get(self.product_inventory_category, 'secondary')
    
    
    
    
    @api.model
    def reset_all_quants(self):
        self.env.cr.execute("""
            DELETE FROM stock_quant;
            ALTER SEQUENCE stock_quant_id_seq RESTART WITH 1;
        """)
        self.env.cr.commit()
        return True

    @api.model
    def recompute_quants(self):
        products = self.env['product.product'].search([('type', '=', 'product')])
        Location = self.env['stock.location']
        for product in products:
            locations = Location.search([('usage', '=', 'internal')])
            for location in locations:
                quantity = self.env['stock.quant']._get_available_quantity(product, location)
                if quantity != 0:
                    self._update_available_quantity(product, location, quantity)
        return True
    
    
    
    
    
    def action_apply_inventory(self):
        _logger.info("Starting action_apply_inventory method")

        
        CycleCountLog = self.env['inventory.cycle.count.log']
        CycleCount = self.env['inventory.cycle.count']
        
        _logger.info(f"Processing {len(self)} quants")
        for quant in self:
            _logger.info(f"Processing quant for product {quant.product_id.name} (ID: {quant.product_id.id})")
            _logger.info(f"Quant inventory_date: {quant.inventory_date}")
            _logger.info(f"Quant Lot ID: {quant.lot_id.id} {quant.lot_id}")
            
            # Find the cycle count with matching inventory_date
            cycle_count = CycleCount.search([
                ('date', '=', quant.inventory_date),
                ('state', '=', 'in_progress')
            ], limit=1)
            
            if cycle_count:
                _logger.info(f"Found matching cycle count: ID {cycle_count.id}")
                
                # Create cycle count log entry
                log_entry = CycleCountLog.create({
                    'cycle_count_id': cycle_count.id,
                    'product_id': quant.product_id.id,
                    'expected_quantity': quant.quantity,  # Changed from inventory_quantity_auto
                    'location_id': quant.location_id.id,
                    'lot_id': quant.lot_id.id,
                    'actual_quantity': quant.inventory_quantity,
                    'actual_count_date': fields.Datetime.now(),
                    'user_id': self.env.user.id,
                })
                _logger.info(f"Created cycle count log entry: ID {log_entry.id}")
                
                # Check if all stock quants for this cycle count have been processed
                remaining_quants = self.search([
                    ('inventory_date', '=', cycle_count.date),
                    ('inventory_quantity', '=', False)  # Uncounted quants
                ])
                
                _logger.info(f"Remaining uncounted quants: {len(remaining_quants)}")
                
                if not remaining_quants:
                    _logger.info("All quants counted. Setting cycle count to 'done'")
                    cycle_count.write({'state': 'done'})
            else:
                _logger.warning(f"No matching cycle count found for date {quant.inventory_date}")
        
        _logger.info("Finished action_apply_inventory method")
        res = super(StockQuant, self).action_apply_inventory()
        _logger.info("Super method completed")
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


        
    
