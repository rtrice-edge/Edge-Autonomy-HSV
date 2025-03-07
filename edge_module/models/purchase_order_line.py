from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, get_lang
from odoo.tools import float_is_zero

from datetime import datetime

import logging
_logger = logging.getLogger(__name__)

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    line_number = fields.Integer()
    # line_display = fields.Char(string='Line', compute='_compute_line_display', store=True)

    qty_open = fields.Float(string='Open Quantity', compute='_compute_qty_open', store=True)
    open_cost = fields.Float(string='Open Cost', compute='_compute_open_cost', store=True)

    # add field for tracking the first arrival of the PO
    po_effective_date = fields.Datetime(string='PO First Arrival', related='order_id.effective_date')

    # cost_objective = fields.Selection(
    #     selection=lambda self: self._get_cost_objective_selection(),
    #     string='Cost Objective',
    #     required=True
    # )

    @api.depends('product_qty', 'price_unit', 'qty_received')
    def _compute_open_cost(self):
        for line in self:
            line.open_cost = line.qty_open * line.price_unit

    @api.depends('product_qty', 'qty_received')
    def _compute_qty_open(self):
        for line in self:
            line.qty_open = line.product_qty - line.qty_received
    
    # @api.depends('line_number')
    # def _compute_line_display(self):
    #     for line in self:
    #         line.line_display = str(line.line_number) if line.line_number else ''
    
    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        # After creation, assign line numbers only if not provided
        for line in lines:
            if line.order_id and not line.line_number:
                # Get highest line number for this PO
                highest_line = self.search([
                    ('order_id', '=', line.order_id.id),
                    ('line_number', '!=', False),
                    ('id', '!=', line.id)  # Exclude current line
                ], order='line_number desc', limit=1)
                
                next_number = (highest_line.line_number or 0) + 1
                line.line_number = next_number
        return lines

    @api.onchange('line_number')
    def _onchange_line_number(self):
        """Handle line number changes and validate"""
        if self.line_number and self.order_id:
            # Get all lines from the current order
            order_lines = self.order_id.order_line - self
            
            # Check for duplicate line numbers manually
            duplicate = any(line.line_number == self.line_number for line in order_lines)
            
            if duplicate:
                warning = {
                    'title': 'Warning!',
                    'message': f'Line number {self.line_number} is already used in this order.'
                }
                self.line_number = False  # Reset the value
                return {'warning': warning}
    

    def _get_jobs_selection(self):
        _logger.info("Starting _get_jobs_selection method")
        jobs = self.env['job'].search([])
        _logger.info(f"Found {len(jobs)} jobs")
        
        # Using False for default value
        selection = [('Unknown', 'Unknown')]
        
        for job in jobs:
            _logger.info(f"Processing job: ID={job.id}, Name={job.name}")
            if job.id and job.name:
                selection.append((str(job.id), job.name))
        
        return selection

    job = fields.Selection(
        selection=_get_jobs_selection,
        string='Jobs',
        required=False,
        default=''  # Use empty string for compatibility
    )

    job_number = fields.Char(
        string='Job Number',
        compute='_compute_job_number',
        store=True,
        default='',  # Use empty string for compatibility
        readonly=True
    )

    # Add related field for purchaser
    purchaser_id = fields.Many2one(
        'res.users',
        string='Purchaser',
        related='order_id.user_id',
        store=True,
        readonly=True
    )

    line_invoice_status = fields.Selection([
        ('no', 'Nothing to Bill'),
        ('to invoice', 'Waiting Bills'),
        ('invoiced', 'Fully Billed'),
    ], string='Billing Status', compute='_get_line_invoice_status', store=True, readonly=True, copy=False, default='no')

    @api.depends('state', 'qty_to_invoice', 'invoice_lines.move_id')
    def _get_line_invoice_status(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for line in self:
            if line.state not in ('purchase', 'done') or line.display_type:
                line.line_invoice_status = 'no'
                continue

            if not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                line.line_invoice_status = 'to invoice'
            elif float_is_zero(line.qty_to_invoice, precision_digits=precision) and line.invoice_lines:
                line.line_invoice_status = 'invoiced'
            else:
                line.line_invoice_status = 'no'

    @api.depends('job')
    def _compute_job_number(self):
        for line in self:
            if line.job and line.job != '':  # Check for both False/None and empty string
                try:
                    job_record = self.env['job'].browse(int(line.job))
                    line.job_number = job_record.number if job_record else ''
                except (ValueError, TypeError):
                    line.job_number = ''
            else:
                line.job_number = ''

    expense_type = fields.Selection([
        ('Unknown', 'Unknown'),  # Use empty string for empty value
        ('subcontractors', 'Subcontractors/Consultants/Outside Professionals'),
        ('raw_materials', 'Inventory (Raw Materials)'),
        ('consumables', 'Consumables'),
        ('small_tooling', 'Small Tooling'),
        ('manufacturing_supplies', 'Manufacturing Supplies'),
        ('engineering_supplies', 'Engineering Supplies'),
        ('office_supplies', 'Office Supplies'),
        ('building_supplies', 'Facilities - Building Supplies'),
        ('janitorial', 'Facilities - Janitorial'),
        ('communications', 'Facilities - Phones/Internet/Communications'),
        ('utilities', 'Facilities - Utilities & Waste'),
        ('flight_ops', 'Flight Ops Materials & Supplies'),
        ('it_hardware', 'IT Hardware'),
        ('it_software', 'IT Software'),
        ('it_services', 'IT Services'),
        ('repairs', 'Repairs & Maintenance'),
        ('business_dev', 'Business Development Expenses'),
        ('training', 'Conference/Seminar/Training Fees'),
        ('licenses', 'Licenses & Permits'),
        ('vehicle', 'Vehicle Supplies'),
        ('equipment_rental', 'Equipment Rental'),
        ('employee_morale', 'Employee Morale Costs'),
        ('safety', 'Safety Supplies'),
        ('marketing', 'Marketing Expenses'),
        ('recruiting', 'Recruiting Costs'),
        ('shipping', 'Shipping & Freight, Packaging Supplies'),
        ('direct_award', 'Direct Award Materials (Cost of Good Sold)'),
        ('capex', 'Capital Expenditures, non-IR&D (>$2,500)'),
    ], string='Expense Type', required=False, default='Unknown')  # Use empty string as default

    # Add fields for tracking stock moves
    move_ids = fields.One2many(
        'stock.move',
        'purchase_line_id',
        string='Stock Moves',
        readonly=True
    )

    # Add effective_date computed field
    effective_date = fields.Datetime(
        string='Effective Date',
        compute='_compute_effective_date',
        store=True,
        help="Latest receipt date of the purchase order line's stock moves"
    )

    line_receipt_status = fields.Selection([
        ('pending', 'Not Received'),
        ('partial', 'Partially Received'),
        ('full', 'Fully Received')
    ], string='Receipt Status', compute='_compute_receipt_status', store=True)

    pop_start = fields.Date(string='POP Start')
    pop_end = fields.Date(string='POP End')

    @api.depends('move_ids.state', 'move_ids.date')
    def _compute_effective_date(self):
        for line in self:
            done_moves = line.move_ids.filtered(lambda m: m.state == 'done')
            if done_moves:
                # Get the latest date from done moves
                line.effective_date = max(move.date for move in done_moves)
            else:
                line.effective_date = False

    @api.depends('move_ids.state', 'move_ids.quantity', 'product_qty')
    def _compute_receipt_status(self):
        for line in self:
            moves = line.move_ids.filtered(lambda m: m.state != 'cancel')
            if not moves:
                line.line_receipt_status = False  # For virtual items/services that don't need receiving
            elif all(m.state == 'done' for m in moves):
                line.line_receipt_status = 'full'
            elif any(m.state == 'done' for m in moves):
                line.line_receipt_status = 'partial'
            else:
                line.line_receipt_status = 'pending'
    

    # expense_type = fields.Selection(
    #     selection=lambda self: self._get_expense_type_selection(self.cost_objective),
    #     string='Cost Element',
    #     required=True
    # )
    # account_number = fields.Char(
    #     string='Account Number',
    #     compute='_compute_account_number',
    #     readonly=True
    # )
    requestor_id = fields.Many2one(
        'res.users', 
        string='Requestor',
        default=lambda self: self.env.user,
        tracking=True,
    )

    # @api.model
    # def _get_cost_objective_selection(self):
    #     cost_objectives = self.env['account.mapping'].search([]).mapped('cost_objective')
    #     return [(co, co) for co in set(cost_objectives)]
    



    
    
    # @api.model
    # def _get_expense_type_selection(self, cost_objective):
    #     domain = [('cost_objective', '=', cost_objective)] if cost_objective else []
    #     expense_types = self.env['account.mapping'].search(domain).mapped('expense_type')
    #     return [(et, et) for et in set(expense_types)]

    # @api.depends('cost_objective', 'expense_type')
    # def _compute_account_number(self):
    #     for line in self:
    #         if line.cost_objective and line.expense_type:
    #             account_mapping = self.env['account.mapping'].search([
    #                 ('cost_objective', '=', line.cost_objective),
    #                 ('expense_type', '=', line.expense_type)
    #             ], limit=1)
    #             line.account_number = account_mapping.account_number if account_mapping else False
    #         else:
    #             line.account_number = False

    # @api.onchange('cost_objective')
    # def _onchange_cost_objective(self):
    #     if self.cost_objective:
    #         self.expense_type = False
    #         expense_type_selection = self._get_expense_type_selection(self.cost_objective)
    #         return {'domain': {'expense_type': [('id', 'in', [sel[0] for sel in expense_type_selection])]}}
    #     else:
    #         self.expense_type = False
    #         return {'domain': {'expense_type': []}}

    
    
    
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
        
        # Logging to confirm ID match and clear action
        _logger.info(f"Product ID: {self.product_id.id}")
        
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


    
    
    # New fields specifically for historical view
    historical_qty_open = fields.Float(string='Historical Open Qty', compute='_compute_historical_values', store=True)
    historical_open_cost = fields.Float(string='Historical Open Cost', compute='_compute_historical_values', store=True)
    historical_receipt_status = fields.Selection([
        ('pending', 'Not Received'),
        ('partial', 'Partially Received'),
        ('full', 'Fully Received')
    ], string='Historical Status', compute='_compute_historical_values', store=True)

    @api.depends('order_id', 'product_qty', 'price_unit', 'move_ids.state', 'move_ids.date')
    def _compute_historical_values(self):
        """
        Compute historical values based on the context date.
        This is the standard compute method used when dependencies change.
        """
        _logger.info('Called _compute_historical_values through standard dependency trigger')
        
        # Set default values
        for line in self:
            line.historical_qty_open = line.qty_open
            line.historical_open_cost = line.open_cost
            line.historical_receipt_status = line.line_receipt_status

    def compute_historical_values_forced(self):
        """
        Force computation of historical values based on the context date.
        This method should be called explicitly when the context changes.
        """
        # _logger.info('Called compute_historical_values_forced')
        historical_date = self.env.context.get('historical_date')
        
        if not historical_date:
            _logger.warning('No historical_date in context, using current values')
            return
        
        # Convert string date to datetime for comparison
        if isinstance(historical_date, str):
            historical_date = fields.Date.from_string(historical_date)
        
        # Add time to make it end of day
        historical_datetime = datetime.combine(historical_date, datetime.max.time())
        # _logger.info(f'Computing historical values as of: {historical_datetime}')
        
        for line in self:
            # Get moves that occurred on or before the historical date
            historical_moves = line.move_ids.filtered(
                lambda m: m.state != 'cancel' and 
                        (m.date and m.date <= historical_datetime)
            )
            
            # Calculate the quantity received as of the historical date
            historical_qty_received = 0.0
            for move in historical_moves:
                if move.state == 'done':
                    # For done moves, add the done quantity to received
                    historical_qty_received += move.product_uom._compute_quantity(
                        move.quantity, line.product_uom
                    )
            
            # Calculate historical open quantity and cost
            line.historical_qty_open = line.product_qty - historical_qty_received
            line.historical_open_cost = line.historical_qty_open * line.price_unit
            
            # Determine historical receipt status
            if not historical_moves and line.order_id.state == 'cancel':
                # No moves and order is cancelled
                line.historical_receipt_status = False
            if not historical_moves:
                # No moves as of the historical date
                line.historical_receipt_status = 'pending'
            elif historical_qty_received >= line.product_qty:
                # Fully received as of the historical date
                line.historical_receipt_status = 'full'
            elif historical_qty_received > 0:
                # Partially received as of the historical date
                line.historical_receipt_status = 'partial'
            else:
                # No receipt as of the historical date
                line.historical_receipt_status = 'pending'