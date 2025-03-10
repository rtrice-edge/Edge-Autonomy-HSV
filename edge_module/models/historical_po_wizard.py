from odoo import models, fields, api
import logging
from dateutil.relativedelta import relativedelta
from datetime import datetime
import calendar

_logger = logging.getLogger(__name__)

class HistoricalPurchaseLinesWizard(models.TransientModel):
    _name = 'historical.purchase.lines.wizard'
    _description = 'Historical Purchase Lines Wizard'

    def _get_last_day_previous_quarter(self):
        """Returns the last day of the previous quarter as default date"""
        today = fields.Date.context_today(self)
        # Get current quarter
        current_month = today.month
        current_quarter = (current_month - 1) // 3 + 1
        
        # Calculate previous quarter
        previous_quarter = current_quarter - 1 if current_quarter > 1 else 4
        year = today.year if current_quarter > 1 else today.year - 1
        
        # Last month of the previous quarter
        last_month = previous_quarter * 3
        
        # Get the last day of the last month of the previous quarter
        last_day = calendar.monthrange(year, last_month)[1]
        
        return fields.Date.to_date(f"{year}-{last_month:02d}-{last_day:02d}")

    date = fields.Date(
        string='As of Date',
        default=_get_last_day_previous_quarter,
        required=True,
        help='View purchase order lines open as of this date'
    )

    def action_view_historical_lines(self):
        """Open purchase order lines view with historical date context"""
        self.ensure_one()
        action = self.env.ref('edge_module.action_historical_purchase_order_lines').read()[0]
        
        # Create domain for lines that existed as of the selected date
        action['domain'] = [('create_date', '<=', self.date)]
        
        # Add historical date to context
        ctx = dict(self.env.context)
        ctx.update({
            'historical_date': self.date,
            'search_default_hist_open_non_service_orders': 1  # Default to open orders
        })
        action['context'] = ctx
        
        # Force compute historical values for all relevant lines
        purchase_lines = self.env['purchase.order.line'].with_context(ctx).search([('create_date', '<=', self.date)])
        _logger.info(f'Found {len(purchase_lines)} purchase lines to compute historical values')
        
        # Call the explicit calculation method
        purchase_lines.compute_historical_values_forced()
        
        action['name'] = f'Open Purchase Lines as of {self.date}'
        return action