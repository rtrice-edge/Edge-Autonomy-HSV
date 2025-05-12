from odoo import models, fields, api, _

from datetime import datetime

import logging
_logger = logging.getLogger(__name__)

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # New fields specifically for historical view
    historical_qty_open = fields.Float(string='Historical Open Qty', compute='_compute_historical_values', store=True)
    historical_open_cost = fields.Float(string='Historical Open Cost', compute='_compute_historical_values', store=True)
    historical_receipt_status = fields.Selection([
        ('pending', 'Not Received'),
        ('partial', 'Partially Received'),
        ('dock_received', 'Received at Dock'),
        ('in_qa', 'In QA Inspection'),
        ('full', 'Fully Received'),
        ('cancel', 'Cancelled')
    ], string='Historical Status', compute='_compute_historical_values', store=True)



    def _compute_historical_values(self):
        """
        Force computation of historical values based on the context date.
        This method should be called explicitly when the context changes.
        """
        historical_date = self.env.context.get('historical_date')
        
        if not historical_date:
            _logger.warning('No historical_date in context, using current values')
            return
        
        # Convert string date to datetime for comparison
        if isinstance(historical_date, str):
            historical_date = fields.Date.from_string(historical_date)
        
        # Add time to make it end of day
        historical_datetime = datetime.combine(historical_date, datetime.max.time())
        _logger.info(f'Computing historical values as of: {historical_datetime}')
        
        for line in self:
            # Skip display type lines
            if line.display_type:
                line.historical_receipt_status = False
                continue

            # if date from the context is 3/14/2020 then recompute each lines receipt status
            # if historical_date.date() == date(2020, 3, 14):
            line._compute_receipt_status()
            line._compute_qty_open()
            line._compute_open_cost()

                
            # Get all related moves as of historical date
            # First through direct relationship
            direct_moves = line.move_ids
            
            # Then through origin and product search to catch all related moves
            all_po_moves = self.env['stock.move'].search([
                ('origin', '=', line.order_id.name),
                ('product_id', '=', line.product_id.id)
            ])
            
            # Combine both move sets
            working_moves = all_po_moves | direct_moves
            
            # Filter for historical view:
            # 1. Exclude cancelled moves
            # 2. For done moves, only include those done before/on the historical date
            historical_moves = working_moves.filtered(
                lambda m: m.state != 'cancel' and 
                        (m.state != 'done' or (m.date and m.date <= historical_datetime))
            )
            
            # Calculate historical received quantity - only count from incoming receipts
            historical_qty_received = 0.0
            for move in historical_moves:
                if move.state == 'done' and move.picking_type_id.id == 1:  # Only count receipt moves
                    historical_qty_received += move.product_uom._compute_quantity(
                        move.quantity, line.product_uom
                    )
            
            # Calculate historical open quantity and cost
            if historical_qty_received >= line.product_qty:
                line.historical_qty_open = 0.0
            else:
                line.historical_qty_open = line.product_qty - historical_qty_received
                
            line.historical_open_cost = line.historical_qty_open * line.price_unit
            
            # Determine historical receipt status - ignoring admin_closed and cancellation
            # since we're looking at what actually happened physically at that time
            
            if line.product_id.type == 'service' or not historical_moves:
                # For service products or no moves
                if historical_qty_received >= line.product_qty:
                    line.historical_receipt_status = 'full'
                elif historical_qty_received > 0:
                    line.historical_receipt_status = 'partial'
                else:
                    line.historical_receipt_status = 'pending'
            elif all(move.state == 'done' for move in historical_moves):
                # All moves were completed as of historical date
                line.historical_receipt_status = 'full'
            elif any(move.state == 'done' and move.picking_type_id.id == 1 for move in historical_moves) and \
                any(move.state != 'done' and move.picking_type_id.id == 5 for move in historical_moves):
                # Received at dock but not yet in inventory as of historical date
                if any(move.state != 'cancel' and move.picking_type_id.id in [9, 11, 12] for move in historical_moves):
                    line.historical_receipt_status = 'in_qa'
                else:
                    line.historical_receipt_status = 'dock_received'
            elif any(move.state == 'done' for move in historical_moves):
                # Some moves were done but not all
                line.historical_receipt_status = 'partial'
            else:
                # No moves were done as of historical date
                line.historical_receipt_status = 'pending'