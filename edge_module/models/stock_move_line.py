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
        update the manufacturing order’s finished lot to match.
        Also, force a write so that the MO record is saved immediately.
        """
        res = super(StockMoveLine, self)._onchange_lot_id() or {}
        if self.production_id and self.lot_id and self.move_id:
            # Check if the production order comes from an RMA BOM
            if self.production_id.bom_id and self.production_id.bom_id.is_rma_bom:
                # Check if this move is for the produced product
                if self.move_id.product_id == self.production_id.product_id:
                    # Update the production order’s finished lot
                    self.production_id.lot_producing_id = self.lot_id
                    # Force a write so that the change is saved
                    self.production_id.write({'lot_producing_id': self.lot_id.id})
                    # Optionally add a warning so the user knows the update occurred
                    res['warning'] = {
                        'title': 'Information',
                        'message': 'The finished lot has been updated.'
                    }
        return res
