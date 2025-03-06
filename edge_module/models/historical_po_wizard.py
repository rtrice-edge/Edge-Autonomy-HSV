from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)

class HistoricalPurchaseLinesWizard(models.TransientModel):
    _name = 'historical.purchase.lines.wizard'
    _description = 'Historical Purchase Lines Wizard'

    date = fields.Date(
        string='As of Date',
        default=fields.Date.context_today,
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