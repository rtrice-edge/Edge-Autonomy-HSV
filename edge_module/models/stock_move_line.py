#odoo procurement category

from odoo import models, fields, api
import math 



class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    noninventorymanufacturer = fields.Char(string='Non-Inventory Manufacturer')

    noninventorymanufacturernumber = fields.Char(string='Non-Inventory Manufacturer Number')

    original_receipt = fields.Char(string='Original Receipt')
    
    def _action_done(self):
        # Get relevant quant details *before* calling super, as super() finalizes the move
        # Identifying the exact quant *before* is tricky. It's easier to get the final state *after*.
        res = super(StockMoveLine, self)._action_done()

        # After the move line is done, find the related quants and record their *current* state
        # This assumes the quant state is final immediately after _action_done completes for the line.
        quants_to_check = self.env['stock.quant']
        for ml in self:
            # Find potentially affected quants based on product, location, lot etc.
            domain = [
                ('product_id', '=', ml.product_id.id),
                ('location_id', 'in', [ml.location_id.id, ml.location_dest_id.id]),
                ('lot_id', '=', ml.lot_id.id), # Handles None lot_id correctly
                # Potentially add package_id, owner_id if used and relevant
            ]
            quants_to_check |= self.env['stock.quant'].search(domain)

        # Remove duplicates and record history
        if quants_to_check:
             # Debounce: Avoid creating history if the last entry for this quant is identical and very recent?
             # For now, let's just create the entry. Optimization can be added if needed.
             quants_to_check._create_history_entry({'source': 'move_line_done', 'move_line_id': self.ids}) # Pass related move line ids if needed

        return res
