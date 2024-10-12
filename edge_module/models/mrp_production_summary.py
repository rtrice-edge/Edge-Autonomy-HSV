from odoo import api, fields, models
from dateutil.relativedelta import relativedelta
from datetime import datetime

class MrpProductionSummary(models.Model):
    _name = 'mrp.production.summary'
    _description = 'Manufacturing Order Summary'

    product_id = fields.Many2one('product.product', string='Product', readonly=True)

    # Dynamic generation of month fields
    for i in range(1, 9):
        month_field = 'month_{}'.format(i)
        month_date = fields.Date.today() + relativedelta(months=i-1)
        month_name = month_date.strftime('%B %Y')
        vars()[month_field] = fields.Float(string=month_name, required=False, readonly=True, digits=(10, 2))


    # Update mon_1 to mon_8 fields with dynamic month names
    for i in range(1, 9):
        month_date = fields.Date.today() + relativedelta(months=i-1)
        month_name = month_date.strftime('%B %Y')
        vars()[f'mon_{i}'] = fields.Html(compute='_compute_monthly_quantities', string=month_name, store=False)


    @api.depends('product_id')
    def _compute_monthly_quantities(self):
        today = fields.Date.today()
        MrpProduction = self.env['mrp.production']

        for record in self:
            for i in range(1, 9):
                # Calculate the start and end date for each month
                month_start = today + relativedelta(months=i-1, day=1)
                month_end = month_start + relativedelta(months=1, days=-1)

                # Get the month name
                month_name = month_start.strftime('%B %Y')

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