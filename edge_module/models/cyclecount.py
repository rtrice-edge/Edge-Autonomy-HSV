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
    ], string='Status', default='draft', compute='_compute_state', store=True)
    log_ids = fields.One2many('inventory.cycle.count.log', 'cycle_count_id', string='Count Logs')
    remaining_items_count = fields.Integer(string='Remaining Items to Count', compute='_compute_remaining_items', store=True)

    @api.depends('date')
    def _compute_remaining_items(self):
        for record in self:
            quants = self.env['stock.quant'].search([('inventory_date', '=', record.date)])
            record.remaining_items_count = len(quants)

    @api.depends('remaining_items_count')
    def _compute_state(self):
        for record in self:
            if record.remaining_items_count == 0 and record.state != 'draft':
                record.state = 'done'
            elif record.state == 'draft' and record.remaining_items_count > 0:
                record.state = 'in_progress'

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

            # Get all products with inventory, ordered by last count date
            all_products = ProductProduct.search([('type', '=', 'product')], order='last_inventory_date asc')

            _logger.error(f"Total products found: {len(all_products)}")

            # Calculate total number of products in each category
            total_a_products = len(all_products.filtered(lambda p: p.product_inventory_category == 'A'))
            total_b_products = len(all_products.filtered(lambda p: p.product_inventory_category == 'B'))
            total_c_products = len(all_products.filtered(lambda p: p.product_inventory_category == 'C'))

            _logger.error(f"Total products - A: {total_a_products}, B: {total_b_products}, C: {total_c_products}")

            # Calculate number of products to count for each category
            count_a = int(total_a_products * (new_record.percent_a / 100))
            count_b = int(total_b_products * (new_record.percent_b / 100))
            count_c = int(total_c_products * (new_record.percent_c / 100))

            _logger.error(f"Products to count - A: {count_a}, B: {count_b}, C: {count_c}")

            # Select products to count
            products_to_count = []
            count_a_actual = count_b_actual = count_c_actual = 0

            for product in all_products:
                if product.product_inventory_category == 'A' and count_a_actual < count_a:
                    products_to_count.append(product.id)
                    count_a_actual += 1
                elif product.product_inventory_category == 'B' and count_b_actual < count_b:
                    products_to_count.append(product.id)
                    count_b_actual += 1
                elif product.product_inventory_category == 'C' and count_c_actual < count_c:
                    products_to_count.append(product.id)
                    count_c_actual += 1
                
                if count_a_actual >= count_a and count_b_actual >= count_b and count_c_actual >= count_c:
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

            # Update last_inventory_date for selected products
            products_to_update = ProductProduct.browse(products_to_count)
            products_to_update.write({'last_inventory_date': new_record.date})
            _logger.error(f"Updated last_inventory_date for {len(products_to_update)} products")

            new_record.write({'state': 'in_progress'})
            _logger.error(f"Updated cycle count record with ID: {new_record.id} to 'in_progress' state")

        except Exception as e:
            _logger.exception("An error occurred in create method of CycleCount:")
            raise

        _logger.error("Finished create method for CycleCount")
    
class CycleCountLog(models.Model):
    _name = 'inventory.cycle.count.log'
    _description = 'Inventory Cycle Count Log'

    cycle_count_id = fields.Many2one('inventory.cycle.count', string='Cycle Count', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    lot_id = fields.Many2one('stock.production.lot', string='Lot/Serial Number')
    expected_quantity = fields.Float(string='Expected Quantity')
    actual_quantity = fields.Float(string='Actual Quantity')
    difference = fields.Float(string='Difference', compute='_compute_difference', store=True)
    planned_count_date = fields.Date(string='Planned Count Date', related='cycle_count_id.date', store=True)
    actual_count_date = fields.Datetime(string='Actual Count Date', default=fields.Datetime.now)
    user_id = fields.Many2one('res.users', string='Counted By', default=lambda self: self.env.user)

    @api.depends('expected_quantity', 'actual_quantity')
    def _compute_difference(self):
        for record in self:
            record.difference = record.actual_quantity - record.expected_quantity