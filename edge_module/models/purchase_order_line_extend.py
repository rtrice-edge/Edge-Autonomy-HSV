from odoo import models, fields, api
from datetime import datetime

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.depends('product_qty', 'qty_received', 'create_date')
    def _compute_qty_open(self):
        """Override to consider historical date from context"""
        historical_date = self.env.context.get('historical_date')
        
        for line in self:
            # Skip calculation for lines created after the historical date
            if historical_date and line.create_date:
                if isinstance(historical_date, str):
                    historical_date = fields.Date.from_string(historical_date)
                
                line_create_date = line.create_date.date()
                if line_create_date > historical_date:
                    line.qty_open = 0.0
                    continue
                
                # Convert to datetime for comparison with move dates (end of day)
                historical_datetime = datetime.combine(historical_date, datetime.max.time())
                
                # Filter stock moves that were done before or on the historical date
                done_moves = line.move_ids.filtered(
                    lambda m: m.state == 'done' and m.date and m.date <= historical_datetime
                )
                
                # Calculate historical received quantity from these moves
                historical_qty_received = sum(move.quantity for move in done_moves) if done_moves else 0.0
                line.qty_open = line.product_qty - historical_qty_received
            else:
                # Regular calculation if no historical date
                line.qty_open = line.product_qty - line.qty_received

    @api.depends('product_qty', 'price_unit', 'qty_open', 'create_date')
    def _compute_open_cost(self):
        """Calculate open cost based on qty_open"""
        historical_date = self.env.context.get('historical_date')
        
        for line in self:
            # Skip calculation for lines created after the historical date
            if historical_date and line.create_date:
                if isinstance(historical_date, str):
                    historical_date = fields.Date.from_string(historical_date)
                
                line_create_date = line.create_date.date()
                if line_create_date > historical_date:
                    line.open_cost = 0.0
                    continue
            
            line.open_cost = line.qty_open * line.price_unit

    @api.depends('move_ids.state', 'move_ids.quantity', 'product_qty', 'create_date')
    def _compute_receipt_status(self):
        """Override to consider historical date from context"""
        historical_date = self.env.context.get('historical_date')
        
        for line in self:
            # Skip calculation for lines created after the historical date
            if historical_date and line.create_date:
                if isinstance(historical_date, str):
                    historical_date = fields.Date.from_string(historical_date)
                
                line_create_date = line.create_date.date()
                if line_create_date > historical_date:
                    line.line_receipt_status = False  # Line didn't exist at this date
                    continue
                
                historical_datetime = datetime.combine(historical_date, datetime.max.time())
                
                # Get all non-canceled moves
                all_moves = line.move_ids.filtered(lambda m: m.state != 'cancel')
                
                # Filter moves that were done by the historical date
                done_moves = all_moves.filtered(
                    lambda m: m.state == 'done' and m.date and m.date <= historical_datetime
                )
                
                # Calculate historical received quantity
                hist_received_qty = sum(move.quantity for move in done_moves) if done_moves else 0.0
                
                if not all_moves:
                    line.line_receipt_status = False  # For virtual items/services
                elif hist_received_qty >= line.product_qty:
                    line.line_receipt_status = 'full'
                elif hist_received_qty > 0:
                    line.line_receipt_status = 'partial'
                else:
                    line.line_receipt_status = 'pending'
            else:
                # Regular calculation if no historical date
                moves = line.move_ids.filtered(lambda m: m.state != 'cancel')
                if not moves:
                    line.line_receipt_status = False  # For virtual items/services
                elif all(m.state == 'done' for m in moves):
                    line.line_receipt_status = 'full'
                elif any(m.state == 'done' for m in moves):
                    line.line_receipt_status = 'partial'
                else:
                    line.line_receipt_status = 'pending'