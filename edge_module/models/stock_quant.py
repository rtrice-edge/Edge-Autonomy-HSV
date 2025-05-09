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
    
    observable_quantity = fields.Float(
        string='Observable Quantity',
        compute='_compute_observable_quantity',
        store=False
    )

    @api.depends('quantity', 'reserved_quantity')
    def _compute_observable_quantity(self):
        for quant in self:
            try:
                quant.observable_quantity = quant.quantity - quant.reserved_quantity
            except Exception as e:
                _logger.error(f"Error computing observable_quantity for quant {quant.id}: {str(e)}")
                quant.observable_quantity = 0.0
    
    
    

    def _get_inventory_category_color(self):
        colors = {'A': 'success', 'B': 'warning', 'C': 'danger'}
        return colors.get(self.product_inventory_category, 'secondary')
    
    
    
    
    # @api.model
    # def reset_all_quants(self):
    #     self.env.cr.execute("""
    #         DELETE FROM stock_quant;
    #         ALTER SEQUENCE stock_quant_id_seq RESTART WITH 1;
    #     """)
    #     self.env.cr.commit()
    #     return True

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
    def _create_history_entry(self, source_info=None):
        """ Helper method to create history entries for the current quant set """
        history_vals_list = []
        for quant in self:
            # Avoid creating history for zero quantity quants if they don't represent a change *to* zero
            # Or simply record everything - let's record everything for now for completeness
            history_vals_list.append({
                'product_id': quant.product_id.id,
                'location_id': quant.location_id.id,
                'lot_id': quant.lot_id.id,
                'package_id': quant.package_id.id,
    
                'quantity': quant.quantity, # The quantity AFTER the change
                'change_date': fields.Datetime.now(),
                'user_id': self.env.user.id,
                # Add source_info if passed, e.g. 'move_line_id': source_info.get('move_line_id')
            })
        if history_vals_list:
            self.env['stock.quant.history'].sudo().create(history_vals_list)


    # # Override for Direct Inventory Adjustments / Apply button on Quant form
    # def _apply_inventory(self):
    #     # Store the quant details *before* the change might happen inside super()
    #     pre_change_details = {
    #         q.id: {'quantity': q.inventory_quantity} # Use inventory_quantity as it's the target
    #         for q in self
    #     }
    #     res = super(StockQuant, self)._apply_inventory()

    #     # After applying, check which quants actually changed quantity
    #     # Note: super() might have merged/deleted/created quants. We need to handle this.
    #     # A simple approach: just record the final state of the affected quants (self) after the operation.
    #     quants_to_record = self.exists() # Filter out potentially deleted quants
    #     if quants_to_record:
    #         quants_to_record._create_history_entry({'source': 'apply_inventory'})

    #     return res



        
    
