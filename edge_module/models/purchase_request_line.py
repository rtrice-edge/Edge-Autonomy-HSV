from odoo import api, fields, models, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)

class PurchaseRequestLine(models.Model):
    _name = 'purchase.request.line'
    _description = 'Purchase Request Line'

    request_id = fields.Many2one('purchase.request', string='Purchase Request', 
                                required=True, ondelete='cascade')
    # purchase_order_id = fields.Many2one('purchase.order', related='request_id.purchase_order_id',
    #                                    string='Purchase Order', store=True)
    purchase_type = fields.Selection([
        ('direct_materials', 'Direct Materials'),
        ('direct_services', 'Direct Services'),
        ('indirect_materials', 'Indirect Materials'),
        ('indirect_services', 'Indirect Services')]
        , string='Purchase Type', required=True)
    product_id = fields.Many2one('product.product', string='Product PN', required=True,
                                domain="[('purchase_ok', '=', True)]")
    name = fields.Text(string='Description', required=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    quantity = fields.Float('Quantity', required=True)
    price_unit = fields.Float('Estimated Unit Cost', required=True)
    price_subtotal = fields.Monetary(compute='_compute_subtotal', string='Subtotal',
                                   store=True, currency_field='currency_id')
    currency_id = fields.Many2one(related='request_id.currency_id')
    company_id = fields.Many2one(related='request_id.company_id')

    expense_type = fields.Selection([
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
    ], string='Expense Type', required=True)

    drawing_revision = fields.Char(string='Drawing Revision')
    manufacturer = fields.Char(string='Manufacturer')
    manufacturer_number = fields.Char(string='Manufacturer PN')

    pop_start = fields.Date(string='POP Start')
    pop_end = fields.Date(string='POP End')

    cage_code = fields.Char(string='CAGE Code')

    @api.onchange('purchase_type')
    def _onchange_purchase_type(self):
        """Update product_id domain and value based on purchase_type selection"""
        domain = [('purchase_ok', '=', True)]
        
        if self.purchase_type == 'direct_materials':
            # Filter to consumables and storable products, excluding "Indirect Misc."
            domain += [
                ('detailed_type', 'in', ['consu', 'product']),
                ('default_code', '!=', 'IndirectMisc')
            ]
            # Clear product_id to force selection from filtered options
            self.product_id = False
            
        elif self.purchase_type == 'indirect_materials':
            # Only allow "Indirect Misc." product
            indirect_misc = self.env['product.product'].search([('default_code', '=', 'IndirectMisc')], limit=1)
            if indirect_misc:
                self.product_id = indirect_misc.id
                domain += [('id', '=', indirect_misc.id)]
            
        elif self.purchase_type == 'direct_services':
            # Only allow "Direct Service" product
            direct_service = self.env['product.product'].search([('default_code', '=', 'DirectService')], limit=1)
            if direct_service:
                self.product_id = direct_service.id
                domain += [('id', '=', direct_service.id)]
            
        elif self.purchase_type == 'indirect_services':
            # Only allow "Indirect Service" product
            indirect_service = self.env['product.product'].search([('default_code', '=', 'IndirectService')], limit=1)
            if indirect_service:
                self.product_id = indirect_service.id
                domain += [('id', '=', indirect_service.id)]
        
        return {'domain': {'product_id': domain}}

    # if a cage_code is entered that is not 5 digits long or alphanumeric, then show a warning
    @api.constrains('cage_code')
    def _check_cage_code(self):
        for line in self:
            if line.cage_code:
                # Check if the cage_code is alphanumeric and exactly 5 characters long
                if len(line.cage_code) != 5 or not line.cage_code.isalnum():
                    raise UserError(_('The CAGE Code must be a 5 digit alphanumeric code. Please check your entry.'))
                
    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise UserError(_('The quantity must be greater than zero. Please check your entry.'))

    # If the pop_start is earlier than today's date then show a user error
    @api.constrains('pop_start')
    def _check_pop_start(self):
        for line in self:
            if line.pop_start and line.pop_start < fields.Date.today():
                raise UserError(_('The Period Of Performance Start date cannot be earlier than today.'))
            
    # If the pop_end is earlier than pop_start date then show a user error
    @api.constrains('pop_end', 'pop_start')
    def _check_pop_end(self):
        for line in self:
            if line.pop_end and line.pop_start and line.pop_end < line.pop_start:
                raise UserError(_('The Period Of Performance End date cannot be earlier than the Period Of Performance Start date.'))

    is_service = fields.Boolean(
        compute='_compute_is_service',
        store=True,
        help="Technical field to indicate if this is a service"
    )
    
    @api.depends('product_id', 'product_id.detailed_type')
    def _compute_is_service(self):
        for line in self:
            line.is_service = line.product_id.detailed_type == 'service' if line.product_id else False

    job = fields.Many2one(
        'job',
        string='Job',
        required=True,
        ondelete='restrict',
        domain=[('active', '=', True)]
    )

    @api.depends('job')
    def _compute_job_number(self):
        for line in self:
            if line.job and line.job != 'Unknown':
                try:
                    job_record = self.env['job'].browse(int(line.job))
                    line.job_number = job_record.number if job_record else ''
                except (ValueError, TypeError, KeyError):
                    line.job_number = ''
            else:
                line.job_number = ''

    job_number = fields.Char(
        string='Job Number',
        compute='_compute_job_number',
        store=True,
        default='',  # Use empty string for compatibility
        readonly=True
    )

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.price_subtotal = line.quantity * line.price_unit

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            if self.product_id.name == "Expense":
                self.name = ''
                self.product_uom_id = False
                self.price_unit = 0.0
            else:
                self.name = self.product_id.display_name
                self.product_uom_id = self.product_id.uom_po_id or self.product_id.uom_id
                self.price_unit = self.product_id.standard_price

    @api.onchange('product_uom_id')
    def _onchange_product_uom_id(self):
        if self.product_id and self.product_uom_id and self.product_id.uom_po_id != self.product_uom_id:
            raise UserError(_('The unit of measure selected does not match the product\'s default unit of measure (%s).') % self.product_id.uom_id.name)
