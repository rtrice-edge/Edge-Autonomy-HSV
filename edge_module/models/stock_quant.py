from odoo import models, api

import logging

_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def print_lots_action(self):
        lot_data = []
        
        print("Self:", self)  # Add this line to inspect the self object
        for quant in self:
            print(self)
            doc = type('', (), {})()  # Create an empty object
            doc.product_id = type('', (), {})()  # Create an empty object for product_id
            doc.product_id.display_name = quant.product_id.display_name
            doc.product_id.default_code = quant.product_id.name
            doc.product_id.name = quant.lot_id.name
            lot_data.append(doc)
        print("Lot Data:", lot_data)  # Add this line to inspect the lot_data list
        _logger.info("Lot Data: %s", lot_data)
        return self.env.ref('stock.action_report_lot_label').report_action(self, data=lot_data)
    
    
