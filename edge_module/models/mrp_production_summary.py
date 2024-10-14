from odoo import api, fields, models
from dateutil.relativedelta import relativedelta
from datetime import datetime

class MrpProductionSummary(models.Model):
    _name = 'mrp.production.summary'
    _description = 'Manufacturing Order Summary'

    product_id = fields.Many2one('product.product', string='Product', readonly=True)

    # Dynamically create fields for months 1 to 8 with names like "October 2024"
    for i in range(1, 9):
        month_date = fields.Date.today() + relativedelta(months=i-1)
        month_name = month_date.strftime('%B %Y')
        vars()[f'month_{i}'] = fields.Char(string=month_name, compute='_compute_monthly_quantities', store=True)

    @api.depends('product_id')
    def _compute_monthly_quantities(self):
        today = fields.Date.today()
        MrpProduction = self.env['mrp.production']

        for record in self:
            for i in range(1, 9):
                # Calculate the start and end date for each month
                month_start = today + relativedelta(months=i-1, day=1)
                month_end = month_start + relativedelta(months=1, days=-1)

                # Compute production quantities for the month
                domain = [
                    ('product_id', '=', record.product_id.id),
                    ('date_start', '>=', month_start),
                    ('date_start', '<=', month_end),
                ]

                total_qty = sum(MrpProduction.search(domain).mapped('product_qty'))
                done_qty = sum(MrpProduction.search(domain + [('state', '=', 'done')]).mapped('qty_producing'))

                # Set the computed values dynamically
                setattr(record, f'month_{i}', f"{done_qty}/{total_qty}")

    @api.model
    def init(self):
        # This method will be called when the model is initialized
        self._update_summary()

    @api.model
    def _update_summary(self):
        # Remove existing records
        self.search([]).unlink()

        # Get unique products from manufacturing orders
        products = self.env['mrp.production'].search([]).mapped('product_id')

        # Create a summary record for each unique product
        for product in products:
            self.create({'product_id': product.id})

    def name_get(self):
        return [(record.id, record.product_id.display_name) for record in self]
    
    def action_view_manufacturing_orders(self):
        self.ensure_one()
        action = self.env.ref('mrp.mrp_production_action').read()[0]
        action['domain'] = [('product_id', '=', self.product_id.id)]
        action['context'] = {'search_default_product_id': self.product_id.id}
        return action