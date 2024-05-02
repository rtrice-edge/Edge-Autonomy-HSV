from odoo import models, fields,api
from datetime import datetime

class DemandForecast(models.Model):
    _name = 'demand.forecast'
    _description = 'Demand Forecast'

    product_id = fields.Many2one('product.product', string='Product', required=True)
    year = fields.Integer(string='Year', required=True, default=lambda self: self._this_week()['year'])
    week_number = fields.Integer(string='Week Number', required=True,  default=lambda self: self._this_week()['week_number'])
    qty = fields.Integer(string='Quantity', required=True)



    _sql_constraints = [
        ('unique_demand_forecast', 'unique(product_id, year, week_number)', 'Demand forecast must be unique for each product, year, and week number.'),
        ('positive_qty', 'check(qty >= 0)', 'Quantity must be a positive value.'),
        ('valid_week_number', 'check(week_number >= 1 AND week_number <= 52)', 'Week number must be between 1 and 52.'),
    ]
    
    @api.model
    def _this_week(self):
        today = datetime.now().date()
        year, week_number, _ = today.isocalendar()
        return {
            'year': year,
            'week_number': week_number
        }