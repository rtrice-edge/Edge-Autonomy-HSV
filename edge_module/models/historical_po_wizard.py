from odoo import models, fields, api
from datetime import datetime

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
        
        # Base domain to filter by creation date
        domain = [('create_date', '<=', self.date)]
        
        # Add filter for open POs if requested
        if self.show_open_only:
            # Find moves received by the historical date
            historical_datetime = datetime.combine(self.date, datetime.max.time())
            
            # Get all picking IDs with date_done <= historical date
            received_pickings = self.env['stock.picking'].search([
                ('date_done', '<=', historical_datetime),
                ('state', '=', 'done')
            ]).ids
            
            # Find all move IDs associated with these pickings
            received_moves = self.env['stock.move'].search([
                ('picking_id', 'in', received_pickings),
                ('state', '=', 'done')
            ])
            
            # Get purchase lines that aren't fully received
            if received_moves:
                # Subquery approach - more efficient for large datasets
                domain += [
                    '|',
                    ('move_ids', 'not in', received_moves.ids),  # Has some moves not received
                    ('product_qty', '>', 0)  # Has quantity to receive
                ]
        
        # Add historical date to context
        ctx = dict(self.env.context)
        ctx.update({'historical_date': self.date})
        
        action['domain'] = domain
        action['context'] = ctx
        action['name'] = f'Open Purchase Lines as of {self.date}'
        return action