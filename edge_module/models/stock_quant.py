from odoo import models, api

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def print_lots(self):

        lot_data = []
        for quant in self:
            # lot_data.append({
            #     'product': quant.product_id.name,
            #     'lot': quant.lot_id.name
            # })
            doc = type('', (), {})()  # Create an empty object
            doc.product_id = type('', (), {})()  # Create an empty object for product_id
            doc.product_id.display_name = quant.product_id.display_name
            doc.product_id.default_code = quant.product_id.name
            doc.product_id.name = quant.lot_id.name
            lot_data.append(doc)
        return self.env.ref('stock.report_lot_label').report_action(self, data={'docs': lot_data})
    