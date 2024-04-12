#odoo procurement category

from odoo import models, fields, api




import logging
_logger = logging.getLogger(__name__)

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'


    costobjective = fields.Selection([
        ('direct', 'Direct'),
        ('g&a', 'G&A'),
        ('engovh', 'Eng OVH'),
        ('manovh', 'Man OVH'),
        ('ir&d', 'IR&D'),
        ('b&p', 'B&P')
    ], string='Cost Objective', required=True ,default='direct')


    expensetype = fields.Selection([
        ('engineeringmaterials ', 'Engineering Materials '),
        ('electronicsmaterials ', 'Electronics Materials '),
        ('inventory/procurementmaterials ', 'Inventory/Procurement Materials '),
        ('composites/assemblymaterials ', 'Composites/Assembly Materials '),
        ('groundsupportmaterials ', 'Ground Support Materials '),
        ('subklabor-engineering ', 'Subk Labor-Engineering '),
        ('subklabor-composites/assembly ', 'Subk Labor-Composites/Assembly '),
        ('packing,postage,andfreight ', 'Packing, Postage, and Freight '),
        ('smalltooling ', 'Small Tooling '),
        ('itservices ', 'IT Services '),
        ('ithardware/peripherals ', 'IT Hardware/Peripherals '),
        ('itsoftware ', 'IT Software '),
        ('professionalservices/consultants ', 'Professional Services/Consultants '),
        ('supplies ', 'Supplies '),
        ('janitorial ', 'Janitorial '),
        ('repairs&maintenance ', 'Repairs & Maintenance '),
        ('equipmentrental ', 'Equipment Rental '),
        ('flighttesting ', 'Flight Testing '),
        ('smalltestequipment ', 'Small Test Equipment '),
        ('wastedisposal ', 'Waste Disposal '),
        ('safety ', 'Safety '),
    ], string='Expense Type', required=True, default='inventory/procurementmaterials ')

    
    fai = fields.Boolean(string='First Article Inspection (FAI)')


    url = fields.Char(string='Link to Prodct')


    vendor_number = fields.Char('Vendor Number')
    
    manufacturer = fields.Char(string='Manufacturer')
    manufacturernumber = fields.Char(string='Manufacturer PN')
    package_unit_price = fields.Float(string='Package Unit Price')

    @api.onchange('product_id')
    def _onchange_product(self):
        self._update_vendor_number()
        self._update_manufacturer()

    # @api.onchange('package_unit_price')
    # def _onchange_package_unit_price(self):
    #     if self.package_unit_price:
    #         product = self.product_id
    #         self.price_unit = self.package_unit_price / self.product_packaging_qty

        # This method is called when the product_id is changed and updates the vendor_number field on the purchase order line
        # there is no price update here
    def _update_vendor_number(self):
        _logger.info('Called _update_vendor_number')
        if self.product_id and self.order_id.partner_id:
            product = self.product_id
            partner_id = self.order_id.partner_id.id
            supplier_info = self.env['product.supplierinfo'].search([
                ('product_tmpl_id', '=', product.product_tmpl_id.id),
                ('partner_id', '=', partner_id)
            ], limit=1)
            if supplier_info:
                _logger.info('called _update_vendor_number if statement and was true')
                self.vendor_number = supplier_info.product_name
            else:
                _logger.info('called _update_vendor_number else statement')
                self.vendor_number = False
    def _update_manufacturer(self):
        # This method is called when the product_id is changed and updates the manufacturer field on the purchase order line
        # there is no price update here
        _logger.info('Called _update_manufacturer')
        if self.product_id:
            product = self.product_id
            self.manufacturer = product.product_tmpl_id.manufacturer
            self.manufacturernumber = product.product_tmpl_id.manufacturernumber
        
    @api.onchange('price_unit')
    def _onchange_vendor_number(self):
        # This method is called when the price_unit is changed.  It looks to see if there is already a vendor price list record
        # with the same product and vendor number.  If there is, it updates the price.  If there is not, it creates a new record.
        _logger.info('Called _onchange_vendor_number')
        if self.vendor_number and self.product_id and self.order_id.partner_id:
            product = self.product_id
            partner_id = self.order_id.partner_id.id
            supplier_info = self.env['product.supplierinfo'].search([
                ('product_tmpl_id', '=', product.product_tmpl_id.id),
                ('partner_id', '=', partner_id),
                ('product_name', '=', self.vendor_number)
            ], limit=1)
            if not supplier_info:
                _logger.info('called _onchange_vendor_number if statement and was not true')
                self.env['product.supplierinfo'].create({
                    'product_tmpl_id': product.product_tmpl_id.id,
                    'partner_id': partner_id,
                    'product_name': self.vendor_number,
                    'price': self.price_unit
                })
            else :
                _logger.info('called _onchange_vendor_number else statement')
                supplier_info.write({
                    'price': self.price_unit
                })


