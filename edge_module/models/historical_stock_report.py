from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class HistoricalStockReport(models.TransientModel):
    _name = 'historical.stock.report'
    _description = 'Historical Stock Report'

    date = fields.Date(string='Date', required=True, default=fields.Date.today)
    location_id = fields.Many2one('stock.location', string='Location', required=True)

    def fetch_stock_at_date(self, date, location_id):
        _logger.info("Fetching stock for date: %s and location ID: %s", date, location_id)

        stock_move_line_model = self.env['stock.move.line']
        products = {}

        # Search for relevant stock move lines
        stock_move_lines = stock_move_line_model.search(
            [
                '|',
                ('location_dest_id', '=', location_id),
                ('location_id', '=', location_id),
                ('state', '=', 'done'),
                ('date', '<=', date),
                ('product_id.type', '=', 'product'),  # Filter for storable products only
            ],
            order="date asc"
        )

        _logger.info("Number of stock move lines found: %d", len(stock_move_lines))

        for line in stock_move_lines:
            product_id = line.product_id.id
            if product_id not in products:
                products[product_id] = {
                    'default_code': line.product_id.default_code,
                    'description': line.product_id.name,
                    'uom': line.product_uom_id.name,
                    'quantity': 0,
                    'cost': line.product_id.standard_price,  # Adjust for FIFO/AVCO if needed
                }
                _logger.info("Initialized product ID %s: %s", product_id, products[product_id])

            if line.location_dest_id.id == location_id:
                products[product_id]['quantity'] += line.qty_done
                _logger.info("Added quantity to product %s: %s", line.product_id.default_code, line.qty_done)
            if line.location_id.id == location_id:
                products[product_id]['quantity'] -= line.qty_done
                _logger.info("Subtracted quantity from product %s: %s", line.product_id.default_code, line.qty_done)

        for product_id, product in products.items():
            product['total_value'] = product['quantity'] * product['cost']
            _logger.info("Calculated total value for product %s: %s", product['default_code'], product['total_value'])

        _logger.info("Completed stock fetching. Total products processed: %d", len(products))
        return list(products.values())


    def action_generate_report(self):
        _logger.info("Generating historical stock report for date: %s, location: %s", self.date, self.location_id.name)

        self.env['historical.stock.report.line'].search([]).unlink()
        _logger.info("Cleared previous report lines.")

        stock_data = self.fetch_stock_at_date(self.date, self.location_id.id)
        _logger.info("Stock data retrieved: %s", stock_data)

        report_lines = self.env['historical.stock.report.line']
        for data in stock_data:
            report_lines.create({
                'default_code': data['default_code'],
                'description': data['description'],
                'uom': data['uom'],
                'quantity': data['quantity'],
                'cost': data['cost'],
                'total_value': data['total_value'],
            })
            _logger.info("Created report line for product: %s", data['default_code'])

        _logger.info("Report generation complete.")
        return {
            'type': 'ir.actions.act_window',
            'name': 'Historical Stock Report',
            'view_mode': 'tree',
            'res_model': 'historical.stock.report.line',
            'target': 'current',
        }


class HistoricalStockReportLine(models.Model):
    _name = 'historical.stock.report.line'
    _description = 'Historical Stock Report Line'

    default_code = fields.Char(string='Default Code')
    description = fields.Char(string='Description')
    uom = fields.Char(string='Unit of Measure')
    quantity = fields.Float(string='Quantity')
    cost = fields.Float(string='Cost')
    total_value = fields.Float(string='Total Value')
