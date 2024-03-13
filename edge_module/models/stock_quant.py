from odoo import models, api

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def print_lots_action(self):
        lot_data = []
        for quant in self:
            print(self)
            doc = type('', (), {})()  # Create an empty object
            doc.product_id = type('', (), {})()  # Create an empty object for product_id
            doc.product_id.display_name = quant.product_id.display_name
            doc.product_id.default_code = quant.product_id.name
            doc.product_id.name = quant.lot_id.name
            lot_data.append(doc)
        print("Lot Data:", lot_data)  # Add this line to inspect the lot_data list
        return self.env.ref('stock.action_report_lot_label').report_action(lot_data)
    