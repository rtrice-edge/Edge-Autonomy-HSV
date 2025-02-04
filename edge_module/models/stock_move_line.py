#odoo procurement category

from odoo import models, fields, api
import math 



class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    noninventorymanufacturer = fields.Char(string='Non-Inventory Manufacturer')

    noninventorymanufacturernumber = fields.Char(string='Non-Inventory Manufacturer Number')

    original_receipt = fields.Char(string='Original Receipt')
    

    @api.onchange('lot_id')
    def _onchange_lot_id_update_production(self):
        """When a lot/serial is selected on an RMA component move,
        update the manufacturing order’s finished lot to match and force a save.
        """
        # We no longer call super() since there's no parent _onchange_lot_id method.
        # reteasting... because we no longer call super in here.
        res = {}
        if self.production_id and self.lot_id and self.move_id:
            # Check if the MO's BOM is flagged as an RMA BOM.
            if self.production_id.bom_id and self.production_id.bom_id.is_rma_bom:
                # If this move line corresponds to the produced product,
                # update the finished lot on the MO.
                if self.move_id.product_id == self.production_id.product_id:
                    self.production_id.lot_producing_id = self.lot_id
                    # Force the change to be saved immediately.
                    self.production_id.write({'lot_producing_id': self.lot_id.id})
                    res = {'warning': {'title': 'Information', 'message': 'The finished lot has been updated.'}}
        return res
