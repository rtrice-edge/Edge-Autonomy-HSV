from odoo import api, fields, models
from dateutil.relativedelta import relativedelta
from datetime import datetime

class MrpProductionSummary(models.Model):
    _name = 'mrp.production.summary'
    _description = 'Manufacturing Order Summary'

    product_id = fields.Many2one('product.product', string='Product', readonly=True)

    # Dynamically create fields for months 1 to 8 with names like "October 2024"
    month_1 = fields.Char(string='Month 1', compute='_compute_monthly_quantities', store=True)
    month_2 = fields.Char(string='Month 2', compute='_compute_monthly_quantities', store=True)
    month_3 = fields.Char(string='Month 3', compute='_compute_monthly_quantities', store=True)
    month_4 = fields.Char(string='Month 4', compute='_compute_monthly_quantities', store=True)
    month_5 = fields.Char(string='Month 5', compute='_compute_monthly_quantities', store=True)
    month_6 = fields.Char(string='Month 6', compute='_compute_monthly_quantities', store=True)
    month_7 = fields.Char(string='Month 7', compute='_compute_monthly_quantities', store=True)
    month_8 = fields.Char(string='Month 8', compute='_compute_monthly_quantities', store=True)

    @api.depends('product_id')
    def _compute_monthly_quantities(self):
        today = fields.Date.today()
        MrpProduction = self.env['mrp.production']

        for record in self:
            for i in range(1, 9):
                # Calculate the start and end date for each month
                month_start = today + relativedelta(months=i-1, day=1)
                month_end = month_start + relativedelta(months=1, days=-1)

                # Get the month name (e.g., "October 2024")
                month_name = month_start.strftime('%B %Y')

                # Compute production quantities for the month
                domain = [
                    ('product_id', '=', record.product_id.id),
                    ('date_planned_start', '>=', month_start),
                    ('date_planned_start', '<=', month_end),
                ]

                total_qty = sum(MrpProduction.search(domain).mapped('product_qty'))
                done_qty = sum(MrpProduction.search(domain + [('state', '=', 'done')]).mapped('qty_producing'))

                # Set the computed values dynamically
                setattr(record, f'month_{i}', f"{month_name}: {done_qty}/{total_qty}")

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