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
    ], string='Cost Objective', required=False ,default='direct')


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
    ], string='Expense Type', required=False, default='inventory/procurementmaterials ')

    
    fai = fields.Boolean(string='First Article Inspection (FAI)')


    url = fields.Char(string='Link to Prodct')


    vendor_number = fields.Char('Vendor Number')
    
    manufacturer = fields.Char(string='Manufacturer')
    manufacturernumber = fields.Char(string='Manufacturer PN')
    package_unit_price = fields.Float(string='Package Unit Price')
    
    
    @api.model
    def create(self, vals):
        _logger.info(f"Before create POL: {vals.get('name')}")
        res = super(PurchaseOrderLine, self).create(vals)
        _logger.info(f"After create POL: {res.name}")
        return res

    def write(self, vals):
        _logger.info(f"Before write POL: {self.mapped('name')}")
        res = super(PurchaseOrderLine, self).write(vals)
        _logger.info(f"After write POL: {self.mapped('name')}")
        return res  

    @api.onchange('product_id')
    def onchange_product_id(self):
        
        res = super(PurchaseOrderLine, self).onchange_product_id()
        if self.order_id.requisition_id:
            requisition_line = self.order_id.requisition_id.line_ids.filtered(lambda x: x.product_id == self.product_id)
            if requisition_line:
                self.name = requisition_line[0].product_description_variants or self.name
        return res
    def _onchange_product(self):
    
        self._update_vendor_number()
        self._update_manufacturer()
        



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
                self.vendor_number = supplier_info.product_name
            else:
                self.vendor_number = False
        # _logger.info('Called _update_product_description')
        # if self.order_id.requisition_id:
        #     _logger.info('Updating product description from PR line')
        #     requisition_lines = self.order_id.requisition_id.line_ids
        #     if self.sequence < len(requisition_lines):
            
        #         requisition_line = requisition_lines[self.sequence - 1]
        #         _logger.info(requisition_line.product_description_variants + "product_description_variants")
        #         _logger.info(requisition_line)
        #         _logger.info(self.sequence)
        #         self.name = requisition_line.product_description_variants
        #     else:
        #         _logger.info('No PR line found for updating product description')
        #         self.name = self.product_id.name
        # else:
        #     _logger.info('No PR found for updating product description')
        #     self.name = self.product_id.name
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


