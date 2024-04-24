#odoo procurement category

from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, get_lang



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

    packaging_currency_id = fields.Many2one('res.currency', string='Packaging Currency', related='company_id.currency_id', readonly=True)
    package_price = fields.Monetary('Price of Package', currency_field='packaging_currency_id', default=0.0, compute='_compute_package_price', store=True)
    package_price_unit = fields.Float(compute='_compute_price_unit', store=True)
    


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

    def _update_manufacturer(self):
        # This method is called when the product_id is changed and updates the manufacturer field on the purchase order line
        # there is no price update here
        _logger.info('Called _update_manufacturer')
        if self.product_id:
            product = self.product_id
            self.manufacturer = product.product_tmpl_id.manufacturer
            self.manufacturernumber = product.product_tmpl_id.manufacturernumber
    def _compute_price_unit_and_date_planned_and_name(self):
        po_lines_without_requisition = self.env['purchase.order.line']
        for pol in self:
            if pol.product_id.id not in pol.order_id.requisition_id.line_ids.product_id.ids:
                po_lines_without_requisition |= pol
                continue
            for index, line in enumerate(pol.order_id.requisition_id.line_ids):
                if index < len(pol.order_id.order_line):
                    pol_line = pol.order_id.order_line[index]
                    pol_line.price_unit = line.product_uom_id._compute_price(line.price_unit, pol_line.product_uom)
                    partner = pol_line.order_id.partner_id or pol_line.order_id.requisition_id.vendor_id
                    params = {'order_id': pol_line.order_id}
                    seller = pol_line.product_id._select_seller(
                        partner_id=partner,
                        quantity=pol_line.product_qty,
                        date=pol_line.order_id.date_order and pol_line.order_id.date_order.date(),
                        uom_id=line.product_uom_id,
                        params=params
                    )
                    if not pol_line.date_planned:
                        pol_line.date_planned = pol_line._get_date_planned(seller).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    product_ctx = {'seller_id': seller.id, 'lang': get_lang(pol_line.env, partner.lang).code}
                    name = pol_line._get_product_purchase_description(pol_line.product_id.with_context(product_ctx))
                    if line.product_description_variants:
                        name += '\n' + line.product_description_variants
                    pol_line.name = name
                    _logger.info(f'Product ID: {pol_line.product_id.default_code}')
                    _logger.info(f'Product Name: {line.product_description_variants}')
                    _logger.info(f'Name: {pol_line.name}')
                    break
        super(PurchaseOrderLine, po_lines_without_requisition)._compute_price_unit_and_date_planned_and_name()

        
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

    @api.depends('product_packaging_qty', 'package_price')
    def _compute_price_unit(self):
            for line in self:
                if line.product_packaging_qty and line.package_price:
                    line.price_unit = line.package_price / line.product_packaging_qty
                else:
                    line.price_unit = 0.0

    @api.depends('product_packaging_qty', 'price_unit')
    def _compute_package_price(self):
            for line in self:
                if line.product_packaging_qty and line.price_unit:
                    line.package_price = line.price_unit * line.product_packaging_qty
                else:
                    line.package_price = 0.0

    @api.onchange('package_price', 'product_packaging_qty')
    def _onchange_package_price(self):
        if self.package_price and self.product_packaging_qty:
            self.package_price_unit = self.package_price / self.product_packaging_qty

    @api.onchange('package_price_unit', 'product_packaging_qty')
    def _onchange_price_unit(self):
        if self.package_price_unit and self.product_packaging_qty:
            self.package_price_unit = self.package_price_unit * self.product_packaging_qty
