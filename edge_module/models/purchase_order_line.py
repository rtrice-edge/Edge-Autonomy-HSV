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


    cost_objective = fields.Selection(
        selection=lambda self: self._get_cost_objective_selection(),
        string='Cost Objective',
        required=True
    )
    expense_type = fields.Selection(
        selection=lambda self: self._get_expense_type_selection(self.cost_objective),
        string='Expense Type',
        required=True
    )
    account_number = fields.Char(
        string='Account Number',
        compute='_compute_account_number',
        readonly=True
    )
    requestor_id = fields.Many2one(
        'res.users', 
        string='Requestor',
        default=lambda self: self.env.user,
        tracking=True,
    )

    @api.model
    def _get_cost_objective_selection(self):
        cost_objectives = self.env['account.mapping'].search([]).mapped('cost_objective')
        return [(co, co) for co in set(cost_objectives)]

    @api.model
    def _get_expense_type_selection(self, cost_objective):
        domain = [('cost_objective', '=', cost_objective)] if cost_objective else []
        expense_types = self.env['account.mapping'].search(domain).mapped('expense_type')
        return [(et, et) for et in set(expense_types)]

    @api.depends('cost_objective', 'expense_type')
    def _compute_account_number(self):
        for line in self:
            if line.cost_objective and line.expense_type:
                account_mapping = self.env['account.mapping'].search([
                    ('cost_objective', '=', line.cost_objective),
                    ('expense_type', '=', line.expense_type)
                ], limit=1)
                line.account_number = account_mapping.account_number if account_mapping else False
            else:
                line.account_number = False

    @api.onchange('cost_objective')
    def _onchange_cost_objective(self):
        if self.cost_objective:
            self.expense_type = False
            expense_type_selection = self._get_expense_type_selection(self.cost_objective)
            return {'domain': {'expense_type': [('id', 'in', [sel[0] for sel in expense_type_selection])]}}
        else:
            self.expense_type = False
            return {'domain': {'expense_type': []}}

    
    
    
    fai = fields.Boolean(string='First Article Inspection (FAI)')


    url = fields.Char(string='Link to Product')


    vendor_number = fields.Char('Vendor Number')
    
    manufacturer = fields.Char(string='Manufacturer')
    manufacturernumber = fields.Char(string='Manufacturer PN')
    package_unit_price = fields.Float(string='Package Unit Price')

    packaging_currency_id = fields.Many2one('res.currency', string='Packaging Currency', related='company_id.currency_id', readonly=True)
    package_price = fields.Monetary('PKG Price', currency_field='packaging_currency_id', default=0.0, store=True)
    product_packaging_qty = fields.Integer(string='PKG Count')
    packaging_qty = fields.Float(related='product_packaging_id.qty')


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

    # @api.onchange('package_unit_price')
    # def _onchange_package_unit_price(self):
    #     if self.package_unit_price:
    #         product = self.product_id
    #         self.price_unit = self.package_unit_price / self.product_packaging_qty
    

    @api.onchange('product_id', 'order_id.partner_id')
    def _onchange_product_partner(self):
        self._update_vendor_number()
        self._update_manufacturer()

        res = super(PurchaseOrderLine, self).onchange_product_id()
        if self.order_id.requisition_id:
            requisition_line = self.order_id.requisition_id.line_ids.filtered(lambda x: x.product_id == self.product_id)
            if requisition_line:
                self.name = requisition_line[0].product_description_variants or self.name
        return res
    

    @api.onchange('vendor_number')
    def _onchange_vendor_number(self):
        for record in self:
            existing_supplier_infos = self.env['product.supplierinfo'].search([
                ('name', '=', record.partner_id.id),
                ('product_name', '!=', record.vendor_number)
            ])
            if not existing_supplier_infos:
                self.env['product.supplierinfo'].create({
                    'name': record.partner_id.id,
                    'product_name': record.vendor_number,
                    # Add any other necessary fields
                })
            else:
                for supplier_info in existing_supplier_infos:
                    supplier_info.product_name = record.vendor_number

            supplier_info_records = self.env['supplier.info'].search([('your_model_id', '=', record.id)])
            for supplier_info_record in supplier_info_records:
                supplier_info_record.vendor_number = record.vendor_number
    
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



    @api.onchange('product_packaging_qty', 'packaging_qty')
    def _onchange_packaging_quantities(self):
        _logger.info('Called _onchange_packaging_quantities')
        if self.product_packaging_qty and self.product_packaging_id:
            self.product_qty = self.product_packaging_qty * self.packaging_qty
        if self.product_qty and self.product_packaging_id:
            self.product_packaging_qty = self.product_qty / self.packaging_qty
        if self.product_qty and self.packaging_qty:
            self.product_packaging_qty = self.product_qty / self.packaging_qty 
        if self.product_packaging_qty and self.price_unit and self.product_packaging_id:
            self.package_price = self.price_unit * self.packaging_qty 

    @api.onchange('package_price')
    def _onchange_package_price(self):
        _logger.info('Called _onchange_package_price')
        if self.package_price and self.product_packaging_id:
            self.price_unit = self.package_price / self.packaging_qty

    @api.onchange('price_unit')
    def _onchange_unit_price(self):
        _logger.info('Called _onchange_unit_price')
        if self.price_unit and self.product_packaging_id:
            self.package_price = self.price_unit * self.packaging_qty

    @api.onchange('product_qty')
    def _onchange_product_qty(self):
        _logger.info('Called _onchange_product_qty')
        if self.product_packaging_id and self.product_qty:
            self.product_packaging_qty = self.product_qty / self.packaging_qty


    @api.onchange('product_packaging_id')
    def _onchange_when_package_changes(self):
        _logger.info('Called _onchange_when_package_changes')
        if self.product_packaging_id:
            self.product_packaging_qty = False
            self.product_qty = False
            self.price_unit = False
            self.package_price = False
