from odoo import models, fields, api
from datetime import datetime

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    
    # New fields specifically for historical view
    historical_qty_open = fields.Float(string='Historical Open Qty', compute='_compute_historical_values', store=False)
    historical_open_cost = fields.Float(string='Historical Open Cost', compute='_compute_historical_values', store=False)
    historical_receipt_status = fields.Selection([
        ('pending', 'Not Received'),
        ('partial', 'Partially Received'),
        ('full', 'Fully Received')
    ], string='Historical Status', compute='_compute_historical_values', store=False)

    @api.depends('product_qty', 'qty_received', 'create_date', 'move_ids', 'price_unit')
    def _compute_historical_values(self):
        """Compute all historical values at once"""
        historical_date = self.env.context.get('historical_date')
        
        for line in self:
            # Initialize with default values
            line.historical_qty_open = 0.0
            line.historical_open_cost = 0.0
            line.historical_receipt_status = False
            
            if not historical_date:
                continue
                
            # Skip lines created after historical date
            if line.create_date:
                if isinstance(historical_date, str):
                    historical_date = fields.Date.from_string(historical_date)
                
                line_create_date = line.create_date.date()
                if line_create_date > historical_date:
                    continue
            
            # Convert to datetime for comparison
            historical_datetime = datetime.combine(historical_date, datetime.max.time())
            
            # Get all non-canceled moves
            all_moves = line.move_ids.filtered(lambda m: m.state != 'cancel')
            
            # Filter moves done by historical date using picking.date_done
            done_moves = all_moves.filtered(
                lambda m: m.state == 'done' and 
                         m.picking_id and  
                         self.env['stock.picking'].browse(m.picking_id.id).date_done and  
                         self.env['stock.picking'].browse(m.picking_id.id).date_done <= historical_datetime
            )
            
            # Calculate historical quantities
            historical_received = sum(move.quantity for move in done_moves) if done_moves else 0.0
            line.historical_qty_open = line.product_qty - historical_received
            line.historical_open_cost = line.historical_qty_open * line.price_unit
            
            # Set receipt status
            if not all_moves:
                line.historical_receipt_status = False  # For services
            elif historical_received >= line.product_qty:
                line.historical_receipt_status = 'full'
            elif historical_received > 0:
                line.historical_receipt_status = 'partial'
            else:
                line.historical_receipt_status = 'pending'