from odoo import models, fields, api

class HistoricalPurchaseLinesWizard(models.TransientModel):
    _name = 'historical.purchase.lines.wizard'
    _description = 'Historical Purchase Lines Wizard'

    date = fields.Date(
        string='As of Date',
        default=fields.Date.context_today,
        required=True,
        help='View purchase order lines open as of this date'
    )

    show_open_only = fields.Boolean(
        string="Show Open Orders Only", 
        default=True,
        help="Show only orders that weren't fully received by the selected date"
    )

    def action_view_historical_lines(self):
        """Open purchase order lines view with historical date context"""
        self.ensure_one()
        action = self.env.ref('edge_module.action_historical_purchase_order_lines').read()[0]
        
        # Create domain to filter by creation date
        domain = [('create_date', '<=', self.date)]
        
        # Add historical date to context
        ctx = dict(self.env.context)
        ctx.update({
            'historical_date': self.date
        })
        
        # Wait for historical values to be computed
        purchase_lines = self.env['purchase.order.line'].search(domain)
        if self.show_open_only:
            # Force computation to update the stored values
            purchase_lines.with_context(historical_date=self.date)._compute_historical_values()
            # Filter to show only open orders
            domain += [('historical_receipt_status', 'in', ['pending', 'partial'])]
        
        action['domain'] = domain
        action['context'] = ctx
        action['name'] = f'Open Purchase Lines as of {self.date}'
        return action