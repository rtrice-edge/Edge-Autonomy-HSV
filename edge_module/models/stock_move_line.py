#odoo procurement category

from odoo import models, fields, api
import math 



class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    noninventorymanufacturer = fields.Char(string='Non-Inventory Manufacturer')

    noninventorymanufacturernumber = fields.Char(string='Non-Inventory Manufacturer Number')

    original_receipt = fields.Char(string='Original Receipt')
    

            
