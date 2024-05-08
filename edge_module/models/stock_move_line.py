#odoo procurement category

from odoo import models, fields, api
import math 



class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    noninventorymanufacturer = fields.Char(string='Non-Inventory Manufacturer')

    noninventorymanufacturernumber = fields.Char(string='Non-Inventory Manufacturer Number')

    original_receipt = fields.Char(string='Original Receipt')
    
    @api.depends('quant_id')
    def _compute_quantity(self):
        """
        This field represents the sum of the move lines `quantity`. It allows the user to know
        if there is still work to do.

        We take care of rounding this value to the nearest whole number using the `ceil` function
        to ensure that the quantity is always rounded up.
        """
        super()._compute_quantity()
        #Changing the quantity to be rounded up
        for move in self:
            move.quantity = math.ceil(move.quantity)
            
