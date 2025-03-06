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

    def action_view_historical_lines(self):
        """Open purchase order lines view with historical date context"""
        self.ensure_one()
        action = self.env.ref('edge_module.action_historical_purchase_order_lines').read()[0]
        
        # Create domain to filter by creation date
        action['domain'] = [('create_date', '<=', self.date)]
        
        # Add historical date to context
        action['context'] = dict(self.env.context)
        action['context'].update({
            'historical_date': self.date
        })
        
        action['name'] = f'Open Purchase Lines as of {self.date}'
        return action
    