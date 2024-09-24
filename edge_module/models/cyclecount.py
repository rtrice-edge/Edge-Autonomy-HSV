from odoo import models, fields, api
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)

class CycleCount(models.Model):
    _name = 'inventory.cycle.count'
    _description = 'Inventory Cycle Count'

    date = fields.Date(string='Cycle Count Date', required=True, default=fields.Date.today)
    count_type = fields.Selection([
        ('full', 'Full'),
        ('monthly', 'Monthly'),
        ('custom', 'Custom')
    ], string='Count Type', required=True, default='full')
    percent_a = fields.Float(string='Percent A', default=100, help="Percentage of A category products to count")
    percent_b = fields.Float(string='Percent B', help="Percentage of B category products to count")
    percent_c = fields.Float(string='Percent C', help="Percentage of C category products to count")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done')
    ], string='Status', default='draft')
    log_ids = fields.One2many('inventory.cycle.count.log', 'cycle_count_id', string='Count Logs')


    @api.onchange('count_type')
    def _onchange_count_type(self):
        if self.count_type == 'full':
            self.percent_a = self.percent_b = self.percent_c = 100
        elif self.count_type == 'monthly':
            self.percent_a, self.percent_b, self.percent_c = 100, 35, 12

    @api.model
    def create(self, vals):
        _logger.error("Starting create method for CycleCount")
        
        new_record = super(CycleCount, self).create(vals)
        
        try:
            ProductProduct = self.env['product.product']
            StockQuant = self.env['stock.quant']

            # Get all products with inventory
            all_products = ProductProduct.search([('type', '=', 'product')])

            _logger.error(f"Total products found: {len(all_products)}")

            # Calculate number of products to count for each category
            total_products = len(all_products)
            count_a = int(total_products * (new_record.percent_a / 100))
            count_b = int(total_products * (new_record.percent_b / 100))
            count_c = int(total_products * (new_record.percent_c / 100))

            _logger.error(f"Products to count - A: {count_a}, B: {count_b}, C: {count_c}")

            # Select products to count
            products_to_count = []
            count_a_actual = count_b_actual = count_c_actual = 0

            for product in all_products:
                if product.product_inventory_category == 'A' and len(products_to_count) < count_a:
                    products_to_count.append(product.id)
                    count_a_actual += 1
                elif product.product_inventory_category == 'B' and count_a <= len(products_to_count) < (count_a + count_b):
                    products_to_count.append(product.id)
                    count_b_actual += 1
                elif product.product_inventory_category == 'C' and (count_a + count_b) <= len(products_to_count) < (count_a + count_b + count_c):
                    products_to_count.append(product.id)
                    count_c_actual += 1
                
                if len(products_to_count) >= (count_a + count_b + count_c):
                    break

            _logger.error(f"Actual products selected - A: {count_a_actual}, B: {count_b_actual}, C: {count_c_actual}")
            _logger.error(f"Total products selected for counting: {len(products_to_count)}")

            # Update inventory_date for selected products in stock.quant
            quants_to_update = StockQuant.search([('product_id', 'in', products_to_count)])
            _logger.error(f"Attempting to update {len(quants_to_update)} stock quants")

            if quants_to_update:
                quants_to_update.write({'inventory_date': new_record.date})
                _logger.error(f"Updated {len(quants_to_update)} stock quants with inventory_date: {new_record.date}")
            else:
                _logger.error("No stock quants found to update")

            new_record.write({'state': 'in_progress'})
            _logger.error(f"Updated cycle count record with ID: {new_record.id} to 'in_progress' state")

        except Exception as e:
            _logger.exception("An error occurred in create method of CycleCount:")
            raise

        _logger.error("Finished create method for CycleCount")
        
        return new_record
    
class CycleCountLog(models.Model):
    _name = 'inventory.cycle.count.log'
    _description = 'Inventory Cycle Count Log'

    cycle_count_id = fields.Many2one('inventory.cycle.count', string='Cycle Count', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    expected_quantity = fields.Float(string='Expected Quantity')
    actual_quantity = fields.Float(string='Actual Quantity')
    difference = fields.Float(string='Difference', compute='_compute_difference', store=True)
    count_date = fields.Datetime(string='Count Date', default=fields.Datetime.now)
    user_id = fields.Many2one('res.users', string='Counted By', default=lambda self: self.env.user)

    @api.depends('expected_quantity', 'actual_quantity')
    def _compute_difference(self):
        for record in self:
            record.difference = record.actual_quantity - record.expected_quantity