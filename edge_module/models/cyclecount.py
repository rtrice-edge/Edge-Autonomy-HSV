from odoo import models, fields, api
from datetime import datetime

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

    @api.onchange('count_type')
    def _onchange_count_type(self):
        if self.count_type == 'full':
            self.percent_a = self.percent_b = self.percent_c = 100
        elif self.count_type == 'monthly':
            self.percent_a, self.percent_b, self.percent_c = 100, 35, 12

    def create_cycle_count(self):
        self.ensure_one()
        ProductProduct = self.env['product.product']
        StockQuant = self.env['stock.quant']

        # Get all products with inventory
        all_products = ProductProduct.search([('type', '=', 'product')])

        # Calculate number of products to count for each category
        total_products = len(all_products)
        count_a = int(total_products * (self.percent_a / 100))
        count_b = int(total_products * (self.percent_b / 100))
        count_c = int(total_products * (self.percent_c / 100))

        # Select products to count
        products_to_count = []
        for product in all_products:
            if product.product_inventory_category == 'A' and len(products_to_count) < count_a:
                products_to_count.append(product.id)
            elif product.product_inventory_category == 'B' and count_a <= len(products_to_count) < (count_a + count_b):
                products_to_count.append(product.id)
            elif product.product_inventory_category == 'C' and (count_a + count_b) <= len(products_to_count) < (count_a + count_b + count_c):
                products_to_count.append(product.id)
            
            if len(products_to_count) >= (count_a + count_b + count_c):
                break

        # Update inventory_date for selected products in stock.quant
        quants_to_update = StockQuant.search([('product_id', 'in', products_to_count)])
        quants_to_update.write({'inventory_date': self.date})

        # Create the cycle count record
        new_cycle_count = self.create({
            'date': self.date,
            'count_type': self.count_type,
            'percent_a': self.percent_a,
            'percent_b': self.percent_b,
            'percent_c': self.percent_c,
            'state': 'in_progress',
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'inventory.cycle.count',
            'res_id': new_cycle_count.id,
            'view_mode': 'form',
            'view_id': self.env.ref('edge_module.view_cycle_count_form').id,
            'target': 'current',
        }