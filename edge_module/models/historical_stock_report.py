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
        location_ids = self.env['stock.location'].search([('id', 'child_of', location_id)]).ids

        stock_move_lines = stock_move_line_model.search(
            [
                '|',
                ('location_dest_id', 'in', location_ids),
                ('location_id', 'in', location_ids),
                ('state', '=', 'done'),
                ('date', '<=', date),
                ('product_id.type', '=', 'product'),
            ],
            order="date asc"
        )

        _logger.info("Number of stock move lines found: %d", len(stock_move_lines))

        for line in stock_move_lines:
            # Convert the move's qty_done to the product's inventory UoM
            converted_qty = line.product_uom_id._compute_quantity(line.qty_done, line.product_id.uom_id)

            # Determine if the move involves a child location of the chosen location
            is_dest_child = line.location_dest_id.id in location_ids
            is_source_child = line.location_id.id in location_ids

            # Add to destination location
            if is_dest_child:
                key = (line.product_id.id, line.location_dest_id.id)
                if key not in products:
                    products[key] = {
                        'default_code': line.product_id.default_code,
                        'description': line.product_id.name,
                        # Use the inventory UoM name for consistency
                        'uom': line.product_id.uom_id.name,
                        'quantity': 0,
                        'cost': line.product_id.standard_price,  # Adjust for FIFO/AVCO if needed
                        'location_name': line.location_dest_id.complete_name,
                        'report_date': date,
                    }
                    _logger.debug("Initialized product-location key %s: %s", key, products[key])
                products[key]['quantity'] += converted_qty
                _logger.debug("Added converted quantity to product-location key %s: %s", key, converted_qty)

            # Subtract from source location
            if is_source_child:
                key = (line.product_id.id, line.location_id.id)
                if key not in products:
                    products[key] = {
                        'default_code': line.product_id.default_code,
                        'description': line.product_id.name,
                        'uom': line.product_id.uom_id.name,
                        'quantity': 0,
                        'cost': line.product_id.standard_price,  # Adjust for FIFO/AVCO if needed
                        'location_name': line.location_id.complete_name,
                        'report_date': date,
                    }
                    _logger.debug("Initialized product-location key %s: %s", key, products[key])
                products[key]['quantity'] -= converted_qty
                _logger.debug("Subtracted converted quantity from product-location key %s: %s", key, converted_qty)

        for (product_id, location_id), product in list(products.items()):
            if product['quantity'] < 0:
                _logger.warning(
                    "Negative stock detected for product %s at location %s: %s",
                    product['default_code'],
                    product['location_name'],
                    product['quantity']
                )
            if product['quantity'] == 0:
                _logger.warning(
                    "Zero stock detected for product %s at location %s",
                    product['default_code'],
                    product['location_name']
                )
                del products[(product_id, location_id)]
                continue
            product['total_value'] = product['quantity'] * product['cost']
            _logger.info(
                "Calculated total value for product %s at location %s: %s",
                product['default_code'],
                product['location_name'],
                product['total_value']
            )

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
                'report_date': self.date,
                'default_code': data['default_code'],
                'location_name': data['location_name'],
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

    report_date = fields.Date(string='Report Date')
    default_code = fields.Char(string='Default Code')
    location_name = fields.Char(string='Location')
    description = fields.Char(string='Description')
    uom = fields.Char(string='Unit of Measure')
    quantity = fields.Float(string='Quantity')
    cost = fields.Float(string='Cost')
    total_value = fields.Float(string='Total Value')
