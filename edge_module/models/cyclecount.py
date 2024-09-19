# models/cycle_count.py
from odoo import models, fields, api
from datetime import datetime

class CycleCount(models.Model):
    _name = 'inventory.cycle.count'
    _description = 'Inventory Cycle Count'

    date = fields.Date(string='Cycle Count Date', required=True, default=fields.Date.today)
    product_counts = fields.One2many('inventory.cycle.count.product', 'cycle_count_id', string='Product Counts')
    # Add these new fields
    count_type = fields.Selection([
        ('full', 'Full'),
        ('monthly', 'Monthly'),
        ('custom', 'Custom')
    ], string='Count Type', required=True, default='full')

    # Modify the existing percent fields
    percent_a = fields.Float(string='Percent A', default=100, help="Percentage of A category products to count")
    percent_b = fields.Float(string='Percent B', help="Percentage of B category products to count")
    percent_c = fields.Float(string='Percent C', help="Percentage of C category products to count")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done')
    ], string='Status', default='draft')

     # Add this new method
    @api.onchange('count_type')
    def _onchange_count_type(self):
        if self.count_type == 'full':
            self.percent_a = 100
            self.percent_b = 100
            self.percent_c = 100
        elif self.count_type == 'monthly':
            self.percent_a = 100
            self.percent_b = 35
            self.percent_c = 12
        # For 'custom', we don't set any values, allowing user input

    @api.model
    def create(self, vals):
        if vals.get('count_type') == 'full':
            vals.update({'percent_a': 100, 'percent_b': 100, 'percent_c': 100})
        elif vals.get('count_type') == 'monthly':
            vals.update({'percent_a': 100, 'percent_b': 35, 'percent_c': 12})
        return super(CycleCount, self).create(vals)


    def generate_product_counts(self):
        self.ensure_one()
        ProductProduct = self.env['product.product']
        StockQuant = self.env['stock.quant']
        CycleCountProduct = self.env['inventory.cycle.count.product']

        # Get all products with inventory
        all_products = ProductProduct.search([('type', '=', 'product')])

        # Get the oldest inventory date for each product
        product_dates = {}
        for product in all_products:
            oldest_quant = StockQuant.search([('product_id', '=', product.id)], order='in_date', limit=1)
            if oldest_quant:
                product_dates[product.id] = oldest_quant.in_date or datetime.min

        # Sort products by oldest inventory date
        sorted_products = sorted(product_dates.items(), key=lambda x: x[1])

        # Calculate number of products to count for each category
        total_products = len(sorted_products)
        count_a = int(total_products * (self.percent_a / 100))
        count_b = int(total_products * (self.percent_b / 100))
        count_c = int(total_products * (self.percent_c / 100))

        # Select products to count
        products_to_count = []
        for product_id, _ in sorted_products:
            product = ProductProduct.browse(product_id)
            if product.product_inventory_category == 'A' and len(products_to_count) < count_a:
                products_to_count.append(product_id)
            elif product.product_inventory_category == 'B' and count_a <= len(products_to_count) < (count_a + count_b):
                products_to_count.append(product_id)
            elif product.product_inventory_category == 'C' and (count_a + count_b) <= len(products_to_count) < (count_a + count_b + count_c):
                products_to_count.append(product_id)
            
            if len(products_to_count) >= (count_a + count_b + count_c):
                break
        products_to_count = ProductProduct.browse(products_to_count)

        # Request count for selected products
        self.request_count(products_to_count)

        # Create cycle count products
        for product in products_to_count:
            # Find the most recent count date for this product
            last_count = CycleCountProduct.search([
                ('product_id', '=', product.id)
            ], order='last_count_date desc', limit=1)

            CycleCountProduct.create({
                'cycle_count_id': self.id,
                'product_id': product.id,
                'last_count_date': last_count.last_count_date if last_count else None,
            })

        self.state = 'in_progress'
        self.state = 'in_progress'
    def request_count(self, products):
        action = self.env.ref('stock.action_stock_request_count')
        if action:
            action_context = {
                'default_product_ids': products.ids,
            }
            action = action.sudo().with_context(action_context).read()[0]
            action['context'] = str(action_context)
            return action
        else:
            # Fallback if the action is not found
            return self.env['ir.actions.act_window']._for_xml_id('stock.action_inventory_form')
    def create_cycle_count(self):
        self.ensure_one()
        new_cycle_count = self.create({
            'date': self.date,
            'count_type': self.count_type,
            # Add other fields as needed
        })
        new_cycle_count.generate_product_counts()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'inventory.cycle.count',
            'res_id': new_cycle_count.id,
            'view_mode': 'form',
            'view_id': self.env.ref('edge_module.view_cycle_count_form').id,
            'target': 'current',
        }
    def check_completion(self):
        self.ensure_one()
        all_products = self.product_counts.mapped('product_id')
        inventory_adjustments = self.env['stock.quant'].search([
            ('product_id', 'in', all_products.ids),
            ('inventory_date', '>=', self.date)
        ])
        if inventory_adjustments and all(p in inventory_adjustments.mapped('product_id') for p in all_products):
            self.state = 'done'

 

class CycleCountProduct(models.Model):
    _name = 'inventory.cycle.count.product'
    _description = 'Inventory Cycle Count Product'

    cycle_count_id = fields.Many2one('inventory.cycle.count', string='Cycle Count', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    last_count_date = fields.Date(string='Last Count Date')