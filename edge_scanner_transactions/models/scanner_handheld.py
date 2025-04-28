
from odoo import models, api

class ScannerHandheld(models.TransientModel):
    _name = 'scanner.handheld'
    _description = 'Scanner Landing'

    def action_inventory_transfer(self):
        # to be implemented: launch inventory transfer flow
        return True
