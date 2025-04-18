from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import format_date
from dateutil.relativedelta import relativedelta
from odoo.tools.misc import clean_context
from .TeamsLib import TeamsLib

import logging
_logger = logging.getLogger(__name__)

class PurchaseRequest(models.Model):
    _name = 'purchase.request'
    _description = 'Purchase Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char('Request Number', readonly=True, default='New', copy=False)
    partner_id = fields.Many2one('res.partner', string='Suggested Vendor', tracking=True,
                             domain="[('supplier_rank', '>', 0), ('active', '=', True)]", 
                             required=False, help="If a supplier is known or suggested for this request, please add in this field. It's not required though.")
    currency_id = fields.Many2one('res.currency', string='Currency', 
                                 default=lambda self: self.env.company.currency_id.id)
    request_line_ids = fields.One2many('purchase.request.line', 'request_id', 
                                      string='Request Lines')
    # urgency = fields.Selection([
    #     ('low', 'Low'),
    #     ('medium', 'Medium'),
    #     ('high', 'High'),
    #     ('production_stoppage', 'Production Stoppage')
    # ], string='Urgency', required=True, default='low', 
    # help="""PO will be placed in 2-4 weeks.
    #         Low: No production impact.
            
    #         PO will be placed in 1-2 weeks.
    #         Medium: Mostly expense items non-production item, production items.

    #         PO will be placed in 2-5 business days.
    #         High: Production items with production impact.

    #         PO will be placed at the same day if the request was created before 3PM local time.
    #         Production Stoppage: An urgent production stoppage (if we do not get an item quickly it will have an impact on our production ability) or an urgent item needed to support our customer.""")

    production_stoppage = fields.Boolean('Production Stoppage', default=False, tracking=True,
        help="Select this option if the request is an production stoppage (if we do not get an item quickly it will have an impact on our production ability) or an urgent item needed to support our customer.")
    production_stoppage_display = fields.Char(string="Production Impact", compute="_compute_production_status")
    date_requested = fields.Date('Date Requested', 
                                default=fields.Date.context_today, readonly=True)
    requester_id = fields.Many2one('res.users', string='Requester', 
                                  default=lambda self: self.env.user.id, readonly=True)
    originator = fields.Many2one('hr.employee', string='Originator', tracking=True, required=True,
                             help="The person who originated the request")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending_validation', 'Pending Validation'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('po_created', 'PO Created'),
        ('cancelled', 'Denied')
    ], string='Status', default='draft', tracking=True)

    company_id = fields.Many2one('res.company', string='Company', 
                                default=lambda self: self.env.company)
    amount_total = fields.Monetary(string='Total', compute='_compute_amount_total',
                                 store=True, currency_field='currency_id')
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order',
                                       readonly=True, copy=False)
    deliver_to = fields.Many2one('hr.employee', string='Internal Recipient', required=False, tracking=True,
                                help="Select the person who the package is to be delivered to when it enters the facility.")
    deliver_to_address = fields.Selection([
        ('edge_slo', 'Edge Autonomy HSV'),
        ('other', 'Other')
    ], string='Final Destination', default='edge_slo', required=True, tracking=True,
    help="Only select 'Other' if the items will be received at Edge Autonomy and then shipped out to someone specific at another location/out in the field.")
    deliver_to_other = fields.Char('External Recipient', tracking=True,
                                   help="The name of the person who will be receiving the package at the final destination.")
    deliver_to_other_address = fields.Char('Final Destination Address', tracking=True)
    deliver_to_other_phone = fields.Char('External Recipient Phone Number', tracking=True,
                                            help="The phone number of the person who will be receiving the package at the final destination.")
    needs_other_delivery = fields.Boolean(compute='_compute_needs_other_delivery', default=False, store=True)
    requester_notes = fields.Text('Requester Notes', tracking=True, help="Please use this area to convey any special ordering instructions, links to products, Contractual or Quality requirements to flow down to the supplier (DPAS, FAI, etc.) or other unique circumstances, such as Currency to use for ordering, attachments contained with the request. or special delivery instructions")
    need_by_date = fields.Date('Need by Date', required=True, tracking=True,
                               help="Provide the Date when you need the item delivered to the delivery address or for the service to begin.")
    purchaser_id = fields.Many2one('res.users', string='Purchaser', tracking=True, 
                              domain=lambda self: [('groups_id', 'in', [self.env.ref('purchase.group_purchase_manager').id])],
                              default=lambda self: self.env['res.users'].search([('email', '=', 'bmccoy@edgeautonomy.io')], limit=1))
    
    resale_designation = fields.Selection([
        ('resale', 'Resale'),
        ('no_resale', 'No Resale')
    ], string='Resale Designation', required=True, tracking=True,
    help="Is the item being ordered for internal Edge use (Resale) or will it be re-sold as part of a deliverable (No Resale)?")

    # Add this field to your PurchaseRequest class
    superadmin_edit_mode = fields.Boolean(
        string='Superadmin Edit Mode',
        default=False,
        help="Technical field to track if superadmin edit mode is active"
    )
    
    # approver_id = fields.Many2one(
    #     'purchase.request.approver', 
    #     string='Approver',
    #     tracking=True
    # )

    can_approve = fields.Boolean(compute='_compute_can_approve', store=False)

    is_level_1_approved = fields.Boolean(default=False)
    is_level_2_approved = fields.Boolean(default=False)
    is_level_3_approved = fields.Boolean(default=False)
    is_level_4_approved = fields.Boolean(default=False)
    is_level_5_approved = fields.Boolean(default=False)
    is_level_6_approved = fields.Boolean(default=False)
    is_level_7_approved = fields.Boolean(default=False)
    is_level_8_approved = fields.Boolean(default=False)
    is_level_9_approved = fields.Boolean(default=False)
    is_level_10_approved = fields.Boolean(default=False)
    is_level_11_approved = fields.Boolean(default=False)
    is_level_12_approved = fields.Boolean(default=False)
    
    approver_level_1 = fields.Many2one(
        'purchase.request.approver', 
        string='Dept Supervisor Approver',
        tracking=True,
        ondelete='restrict',
        domain="[('manager_level', '=', 'dept_supv')]",
        help="Department Supervisor who will approve this request"
    )

    needs_approver_level_1 = fields.Boolean(
        compute='_compute_approvers_needed', default=False, store=True
    )

    approver_level_2 = fields.Many2one(
        'purchase.request.approver', 
        string='Dept Manager Approver',
        tracking=True,
        ondelete='restrict',
        domain="[('manager_level', '=', 'dept_mgr')]",
        help="Department Manager who will approve this request"
    )

    needs_approver_level_2 = fields.Boolean(
        compute='_compute_approvers_needed', default=False, store=True
    )

    approver_level_3 = fields.Many2one(
        'purchase.request.approver', 
        string='Program Manager Approver',
        tracking=True,
        ondelete='restrict',
        domain="[('manager_level', '=', 'prog_mgr')]",
        help="Program Manager who will approve this request"
    )

    needs_approver_level_3 = fields.Boolean(
        compute='_compute_approvers_needed', default=False, store=True
    )

    approver_level_4 = fields.Many2one(
        'purchase.request.approver', 
        string='Supply Chain Manager Approver',
        tracking=True,
        ondelete='restrict',
        domain="[('manager_level', '=', 'sc_mgr')]",
        help="Supply Chain Manager who will approve this request"
    )

    needs_approver_level_4 = fields.Boolean(
        compute='_compute_approvers_needed', default=False, store=True
    )

    approver_level_5 = fields.Many2one(
        'purchase.request.approver', 
        string='Department Director Approver',
        tracking=True,
        ondelete='restrict',
        domain="[('manager_level', '=', 'dept_dir')]",
        help="Department Director who will approve this request"
    )

    needs_approver_level_5 = fields.Boolean(
        compute='_compute_approvers_needed', default=False, store=True
    )

    approver_level_6 = fields.Many2one(
        'purchase.request.approver', 
        string='Site GM Approver',
        tracking=True,
        ondelete='restrict',
        domain="[('manager_level', '=', 'gm_coo')]",
        help="Site GM who will approve this request"
    )

    needs_approver_level_6 = fields.Boolean(
        compute='_compute_approvers_needed', default=False, store=True
    )

    approver_level_7 = fields.Many2one(
        'purchase.request.approver', 
        string='CTO Approver',
        tracking=True,
        ondelete='restrict',
        domain="[('manager_level', '=', 'cto')]",
        help="CTO who will approve this request"
    )

    needs_approver_level_7 = fields.Boolean(
        compute='_compute_approvers_needed', default=False, store=True
    )

    approver_level_8 = fields.Many2one(
        'purchase.request.approver', 
        string='CGO Approver',
        tracking=True,
        ondelete='restrict',
        domain="[('manager_level', '=', 'cgo')]",
        help="CGO who will approve this request"
    )

    needs_approver_level_8 = fields.Boolean(
        compute='_compute_approvers_needed', default=False, store=True
    )

    approver_level_9 = fields.Many2one(
        'purchase.request.approver', 
        string='COO Approver',
        tracking=True,
        ondelete='restrict',
        domain="[('manager_level', '=', 'coo')]",
        help="COO who will approve this request"
    )

    needs_approver_level_9 = fields.Boolean(
        compute='_compute_approvers_needed', default=False, store=True
    )

    approver_level_10 = fields.Many2one(
        'purchase.request.approver', 
        string='CPO Approver',
        tracking=True,
        ondelete='restrict',
        domain="[('manager_level', '=', 'cpo')]",
        help="CPO who will approve this request"
    )

    needs_approver_level_10 = fields.Boolean(
        compute='_compute_approvers_needed', default=False, store=True
    )

    approver_level_11 = fields.Many2one(
        'purchase.request.approver', 
        string='CFO Approver',
        tracking=True,
        ondelete='restrict',
        domain="[('manager_level', '=', 'cfo')]",
        help="CFO who will approve this request"
    )

    needs_approver_level_11 = fields.Boolean(
        compute='_compute_approvers_needed', default=False, store=True
    )

    approver_level_12 = fields.Many2one(
        'purchase.request.approver', 
        string='CEO Approver',
        tracking=True,
        ondelete='restrict',
        domain="[('manager_level', '=', 'ceo')]",
        help="CEO who will approve this request"
    )

    needs_approver_level_12 = fields.Boolean(
        compute='_compute_approvers_needed', default=False, store=True
    )

    submit_date = fields.Datetime(string='Submit Date', readonly=True, help="Date when the request was submitted for approval")
    validate_date = fields.Datetime(string='Validate Date', readonly=True, help="Date when the request was validated")
    approve_date = fields.Datetime(string='Approve Date', readonly=True, help="Date when the request was approved")
    po_create_date = fields.Datetime(string='PO Create Date', readonly=True, help="Date when the purchase order was created")

    def action_unlock_fields(self):
        """Unlock all readonly fields for super admin users"""
        self.write({'superadmin_edit_mode': True})
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_lock_fields(self):
        """Lock fields back to their normal state"""
        self.write({'superadmin_edit_mode': False})
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    
    # def action_open_import_wizard(self):
    #     """Open the import wizard for Excel template - bypass form validation"""
    #     self.ensure_one()
        
    #     # Skip form validation by using a try/except block
    #     try:
    #         # Check state - only allow import in draft state
    #         if self.state != 'draft':
    #             return {
    #                 'type': 'ir.actions.client',
    #                 'tag': 'display_notification',
    #                 'params': {
    #                     'title': _('Warning'),
    #                     'message': _('You can only import data in draft state.'),
    #                     'sticky': False,
    #                     'type': 'warning',
    #                 }
    #             }
            
    #         # Store current values of required fields to restore later
    #         originator_id = self.originator.id if self.originator else False
    #         need_by_date = self.need_by_date
    #         resale_designation = self.resale_designation
            
    #         # Temporarily set required fields to avoid validation errors
    #         temp_vals = {}
    #         if not self.originator:
    #             temp_vals['originator'] = self.env['hr.employee'].search([], limit=1).id
    #         if not self.need_by_date:
    #             temp_vals['need_by_date'] = fields.Date.today()
    #         if not self.resale_designation:
    #             temp_vals['resale_designation'] = 'resale'
                
    #         # Apply temporary values if needed
    #         if temp_vals:
    #             self.with_context(skip_validation=True).write(temp_vals)
            
    #         # Return action to open wizard
    #         result = {
    #             'name': _('Import Purchase Request'),
    #             'type': 'ir.actions.act_window',
    #             'res_model': 'purchase.request.import.wizard',
    #             'view_mode': 'form',
    #             'target': 'new',
    #             'context': {
    #                 'default_filename': 'PR_Request_Template.xlsx',
    #                 'active_id': self.id,
    #                 'active_model': 'purchase.request',
    #                 'form_view_initial_mode': 'edit',
    #             }
    #         }
            
    #         # Restore original values
    #         if temp_vals:
    #             restore_vals = {
    #                 'originator': originator_id,
    #                 'need_by_date': need_by_date,
    #                 'resale_designation': resale_designation
    #             }
    #             self.with_context(skip_validation=True).write(restore_vals)
                
    #         return result
    #     except Exception as e:
    #         # If any error occurs, still open the wizard
    #         return {
    #             'name': _('Import Purchase Request'),
    #             'type': 'ir.actions.act_window',
    #             'res_model': 'purchase.request.import.wizard',
    #             'view_mode': 'form',
    #             'target': 'new',
    #             'context': {
    #                 'default_filename': 'PR_Request_Template.xlsx',
    #             }
    #         }
    
    def _compute_production_status(self):
        for record in self:
            record.production_stoppage_display = "Production Stoppage" if record.production_stoppage else ""

    @api.depends('deliver_to_address')
    def _compute_needs_other_delivery(self):
        for record in self:
            if record.deliver_to_address == 'other':
                self.needs_other_delivery = True
                self.deliver_to = False
            else:
                self.needs_other_delivery = False

    @api.onchange('originator')
    def _onchange_originator(self):
        if self.originator and not self.deliver_to and self.deliver_to_address == 'edge_slo':
            self.deliver_to = self.originator.id

    # workhorse function to determine which levels of approvers are needed for this request
    @api.depends('state', 'amount_total', 'request_line_ids.job', 'request_line_ids.expense_type')
    def _compute_approvers_needed(self):
        # _logger.info("Computing approvers needed for %s requests", len(self))
        for request in self:
            # Only compute when the request is in draft state.
            if request.state in ['draft','pending_validation']:
                # Gather information from the request lines.
                line_jobs = [line.job.id for line in request.request_line_ids if line.job]
                line_expense_types = [line.expense_type for line in request.request_line_ids]
                # _logger.info("Line Jobs: %s", line_jobs)
                # _logger.info("Line Expense Types: %s", line_expense_types)

                # Also collect job names (if you use the job’s name for the 'contains' test)
                line_job_names = [line.job.name for line in request.request_line_ids if line.job and line.job.name]

                # _logger.info("Line Job Names: %s", line_job_names)

                # Reset all approver flags to False
                for level in range(1, 13):
                    setattr(request, f'needs_approver_level_{level}', False)

                # Prepare a search domain to get rules that match the amount and either have an expense type or a job set.
                # (We will later check the job_text condition in Python.)
                approval_matrix_domain = [
                    ('min_amount', '<=', request.amount_total),
                    ('max_amount', '>', request.amount_total),
                    '|', '|',
                    ('expense_type', 'in', line_expense_types),
                    ('job_id', '!=', False),
                    ('job_text', '!=', False),
                ]
                approval_matrix_rules = self.env['approval.matrix'].search(approval_matrix_domain)

                level_map = {
                    'dept_supv': 1,
                    'dept_mgr': 2,
                    'prog_mgr': 3,
                    'sc_mgr': 4,
                    'dept_dir': 5,
                    'gm_coo': 6,
                    'cto': 7,
                    'cgo': 8,
                    'coo': 9,
                    'cpo': 10,
                    'cfo': 11,
                    'ceo': 12
                }

                has_approver = False

                for rule in approval_matrix_rules:
                    applicable = False

                    # (a) Check if the rule applies because of expense type.
                    if rule.expense_type and rule.expense_type in line_expense_types:
                        applicable = True

                    # (b) Check if the rule applies because of a job match.
                    #     The rule might be defined via a many2one job (with a comparison of "is")
                    #     or via text (with a comparison of "contains").
                    # _logger.info("Starting inner job loop")
                    if rule.job_id or rule.job_text:
                        # _logger.info("Rule has job_id or job_text")
                        # _logger.info("Job comparison: %s", rule.job_comparison)
                        if rule.job_comparison == 'is' and rule.job_id:
                            # _logger.info("Checking if rule job_id is in line_jobs")
                            if rule.job_id.id in line_jobs:
                                # _logger.info("Rule job_id is in line_jobs")
                                applicable = True
                        elif rule.job_comparison == 'contains' and rule.job_text:
                            # _logger.info("Checking if rule job_text is in line_job_names")
                            # Check if any job name contains the provided text (case-insensitive).
                            if any(rule.job_text in (job_name or '') for job_name in line_job_names):
                                # _logger.info("Rule job_text is in line_job_names")
                                applicable = True

                    # _logger.info("Rule is applicable: %s", applicable)
                    # If this rule is applicable, set the corresponding approver level flags.
                    if applicable:
                        _logger.info("Rule is applicable: %s", rule)
                        # Instead of iterating through all 12 levels, iterate through the approver levels in the rule
                        for i in range(1, 13):
                            _logger.info("Checking approver level %d", i)
                            approver_level_value = getattr(rule, f'approver_level_{i}', False)
                            if approver_level_value:
                                _logger.info("Approver level value %d: %s", i, approver_level_value)
                                # Get the numeric level from the level_map using the approver_level value
                                level_number = level_map.get(approver_level_value)
                                _logger.info("Level number: %s", level_number)
                                if level_number:
                                    # Set the corresponding flag to True
                                    setattr(request, f'needs_approver_level_{level_number}', True)
                                    _logger.info("Set needs_approver_level_%d to True", level_number)
                                    has_approver = True

                # _logger.info("Has approver: %s", has_approver)
                # If no rules set any approver level, then default to level 2.
                if not has_approver:
                    request.needs_approver_level_2 = True
        

    longest_lead_time = fields.Integer(
        compute='_compute_longest_lead_time',
        help="Longest lead time in days among selected products"
    )

    longest_lead_product_id = fields.Many2one(
        'product.product',
        compute='_compute_longest_lead_time',
        help="Product with the longest lead time"
    )

    earliest_possible_date = fields.Date(
        compute='_compute_earliest_possible_date',
        help="Earliest possible delivery date based on product lead times"
    )

    @api.depends('request_line_ids.product_id', 'partner_id')
    def _compute_longest_lead_time(self):
        for record in self:
            max_lead_time = 0
            max_lead_product = False
            
            for line in record.request_line_ids:
                if line.product_id:
                    # Try to get supplier info for selected vendor first
                    seller = line.product_id._select_seller(
                        partner_id=record.partner_id,
                        quantity=line.quantity,
                        date=fields.Date.today(),
                    )
                    # If no seller found for partner, get first supplier
                    if not seller:
                        seller = line.product_id._select_seller(
                            quantity=line.quantity,
                            date=fields.Date.today(),
                        )
                    lead_time = seller.delay if seller else line.product_id.sale_delay
                    
                    if lead_time > max_lead_time:
                        max_lead_time = lead_time
                        max_lead_product = line.product_id

            record.longest_lead_time = max_lead_time
            record.longest_lead_product_id = max_lead_product

    @api.depends('longest_lead_time')
    def _compute_earliest_possible_date(self):
        for record in self:
            record.earliest_possible_date = fields.Date.today() + relativedelta(days=record.longest_lead_time)

    @api.onchange('need_by_date', 'earliest_possible_date')
    def _onchange_need_by_date(self):
        if self.need_by_date and self.earliest_possible_date:
            # today = fields.Date.today()
            # one_week_later = today + relativedelta(days=7)
            # two_weeks_later = today + relativedelta(days=14)
            
            # if self.need_by_date <= one_week_later:
            #     self.urgency = 'high'
            # elif self.need_by_date <= two_weeks_later:
            #     self.urgency = 'medium'
            # else:
            #     self.urgency = 'low'
            # If the requested date is earlier than today's date then show a user error
            if self.need_by_date < fields.Date.today():
                raise UserError(_("Need by date cannot be in the past."))
            # If the requested date is earlier than the earliest possible date then show a warning
            elif self.need_by_date < self.earliest_possible_date:
                return {
                    'warning': {
                        'title': _('Lead Time Warning'),
                        'message': _(
                            "The requested date %(requested_date)s may not be possible due to product lead times.\n"
                            "The product '%(product)s' has a lead time of %(lead_time)d days, "
                            "making %(earliest_date)s the earliest possible delivery date.",
                            requested_date=format_date(self.env, self.need_by_date),
                            product=self.longest_lead_product_id.display_name,
                            lead_time=self.longest_lead_time,
                            earliest_date=format_date(self.env, self.earliest_possible_date)
                        )
                    }
                }

    invoice_approver_id = fields.Many2one('res.users', string='Invoice Approver', 
        help="Individual who will approve the Supplier's invoice (cannot be Requistion Writer or Buyer). Only required if requesting a service")

    # @api.constrains('request_line_ids', 'invoice_approver_id', 'state')
    # def _check_invoice_approver(self):
    #     for record in self:
    #         has_services = any(line.product_id.detailed_type == 'service' 
    #                         for line in record.request_line_ids)
    #         if has_services and not record.invoice_approver_id and record.state != 'draft':
    #             raise ValidationError(_("Invoice Approver is required when requesting services."))
       
    lines_have_services = fields.Boolean(
        compute='_compute_lines_have_services',
        help="Technical field to indicate if any lines' products are services"
    )

    # @api.depends('purchaser_id')
    # def _subscribe_purchaser(self):
    #     for record in self:
    #         if record.purchaser_id:
    #             record.message_subscribe(
    #                 partner_ids=[record.purchaser_id.partner_id.id]
    #             )

    @api.depends('request_line_ids.product_id', 'request_line_ids.product_id.detailed_type')
    def _compute_lines_have_services(self):
        for record in self:
            record.lines_have_services = any(
                line.is_service
                for line in record.request_line_ids
    )
    
    @api.depends('request_line_ids.price_subtotal')
    def _compute_amount_total(self):
        for request in self:
            request.amount_total = sum(request.request_line_ids.mapped('price_subtotal'))

    def action_view_purchase_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'res_id': self.purchase_order_id.id,
            'target': 'current',
        }
    
    # if any needs_approval_level_x are true and the corresponding is_level_x_approved is false then return false, otherwise return true
    def is_fully_approved(self):
        for record in self:
            for i in range(1, 13):
                needs_approver = getattr(record, f'needs_approver_level_{i}')
                is_approved = getattr(record, f'is_level_{i}_approved')
                if needs_approver and not is_approved:
                    return False
        return True
            


    def action_submit(self):
        if not self.request_line_ids:
            raise UserError(_("You cannot submit a purchase request with no request lines."))
        if self.amount_total <= 0:
            raise UserError(_("You cannot submit a purchase request with a total amount of $0."))
        
        self.submit_date = fields.Datetime.now()

        self.write({'state': 'pending_validation'})

        # Find the recipient user
        recipient_1 = self.env['res.users'].search([('email', '=', 'vstefo@edgeautonomy.io')], limit=1)

        # Check if recipient was found and has a valid email
        if not recipient_1 or not recipient_1.email:
            _logger.error(f"Could not find valid recipient email for user: vstefo@edgeautonomy.io")
            return

        # Get the email directly from the user record
        recipient_email = recipient_1.email
        
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = f"{base_url}/web#id={self.id}&view_type=form&model={self._name}"
        url_text = "View Purchase Request"
        
        title = "Purchase Request Validation Needed"
        
        # Construct message
        message = f"""
                A new Purchase Request {self.name} was submitted and is awaiting validation<br>
                Request details:<br>
                - Requester: {self.requester_id.name}<br>
                - Need by Date: {self.need_by_date}<br>
                - Production Impact: {self.production_stoppage_display}<br>
                - Total Amount: {self.currency_id.symbol} {self.amount_total:,.2f}
                """
        
        # try:
            # Send message
        teams_lib = TeamsLib()
        teams_lib.send_message(recipient_email, message, title, url, url_text)

        #     if result:
        #         _logger.info(f"Successfully sent Teams notification to {recipient_email}")
        #     else:
        #         _logger.error(f"Failed to send Teams notification to {recipient_email}")
        # except Exception as e:
        #     _logger.error(f"Error sending Teams notification: {str(e)}", exc_info=True)

    def action_validate(self):
        self.validate_date = fields.Datetime.now()
        self.write({'state': 'pending_approval'})
        self._notify_next_approver()



    def _notify_next_approver(self):
        self.ensure_one()

        recipient = False

        # if self.needs_approver_level_x and not self.is_level_x_approved then set recipient to the corresponding approver_level_x
        for i in range(1, 13):
            if getattr(self, f'needs_approver_level_{i}') and not getattr(self, f'is_level_{i}_approved'):
                recipient = getattr(self, f'approver_level_{i}')
                break

        if recipient and recipient.user_id.partner_id:

            recipient_email = recipient.user_id.partner_id.email
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            
            url = False
            if recipient.user_id.has_group('base.group_portal'):
                url = f"{base_url}/my/purchase_requests/{self.id}"
            else:
                url = f"{base_url}/web#id={self.id}&view_type=form&model={self._name}"

            url_text = "View Purchase Request"
            
            title = "Purchase Request Approval Needed"
            # Construct message
            message = f"""
                    You have been assigned as an approver for {self.name}<br>
                    Request details:<br>
                    - Requester: {self.requester_id.name}<br>
                    - Need by Date: {self.need_by_date}<br>
                    - Total Amount: {self.currency_id.symbol} {self.amount_total:,.2f}
                    """
            # Send message
            TeamsLib().send_message(recipient_email, message, title, url, url_text)


            # post a message in chatter tagging the next approver
            partner_to_notify = recipient.user_id.partner_id
            self.message_post(
                body=f"{partner_to_notify.name}, please approve this purchase request.",
                message_type='notification',
                subtype_xmlid='mail.mt_comment',
                partner_ids=[partner_to_notify.id]  # This is what actually tags the user
            )
            
            # if success:
            #     _logger.info("Test message sent successfully.")
            # else:
            #     _logger.error("Failed to send test message.")


    def action_approve(self):
        # if needs_approver_level_x and not is_level_x_approved then set is_level_x_approved to true
        approved_something = False
        
        for i in range(1, 13):
            if getattr(self, f'needs_approver_level_{i}') and not getattr(self, f'is_level_{i}_approved'):
                setattr(self, f'is_level_{i}_approved', True)
                approved_something = True
                break
        
        if not approved_something:
            raise UserError(_("It seems you have already approved this request or it does not require your approval."))
        
        self.message_post(
            body=_("Approved"),
            message_type='notification',
            subtype_xmlid='mail.mt_comment'
        )
        
        if self.is_fully_approved():

            self.approve_date = fields.Datetime.now()
            self.write({'state': 'approved'})

            # Find the recipients
            recipient_1 = self.purchaser_id
            recipient_2 = self.originator

            # Get the email addresses, if available
            recipient_1_email = recipient_1.email if recipient_1 and hasattr(recipient_1, 'email') else False
            recipient_2_email = recipient_2.work_email if recipient_2 and hasattr(recipient_2, 'work_email') else False
            
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = f"{base_url}/web#id={self.id}&view_type=form&model={self._name}"
            url_text = "View Purchase Request"
            
            title = "Purchase Request Has Been Fully Approved"
            
            # Construct message
            message = f"""
                    A Purchase Request {self.name} was fully approved<br>
                    Request details:<br>
                    - Originator: {self.originator.name}<br>
                    - Requester: {self.requester_id.name}<br>
                    - Need by Date: {self.need_by_date}<br>
                    - Production Impact: {self.production_stoppage_display}<br>
                    - Total Amount: {self.currency_id.symbol} {self.amount_total:,.2f}
                    """
            
            # Send message to purchaser
            if recipient_1_email:
                try:
                    result = TeamsLib().send_message(recipient_1_email, message, title, url, url_text)
                    if result:
                        _logger.info(f"Successfully sent Teams notification to purchaser {recipient_1_email}")
                    else:
                        _logger.error(f"Failed to send Teams notification to purchaser {recipient_1_email}")
                except Exception as e:
                    _logger.error(f"Error sending Teams notification to purchaser: {str(e)}", exc_info=True)
            else:
                _logger.warning("Could not find valid email for purchaser, notification not sent")
            
            # Send message to originator if they have a work email
            if recipient_2_email:
                try:
                    result = TeamsLib().send_message(recipient_2_email, message, title, url, url_text)
                    if result:
                        _logger.info(f"Successfully sent Teams notification to originator {recipient_2_email}")
                    else:
                        _logger.error(f"Failed to send Teams notification to originator {recipient_2_email}")
                except Exception as e:
                    _logger.error(f"Error sending Teams notification to originator: {str(e)}", exc_info=True)
            else:
                _logger.warning("Could not find valid work_email for originator, notification not sent")
        else:
            self._notify_next_approver()
    

    def action_merge_requests(self):
        if len(self) < 2:
            raise UserError(_("Please select at least two purchase requests to merge."))
        
        # Check if all requests have the same partner
        if len(self.mapped('partner_id')) > 1:
            raise UserError(_("All selected purchase requests must have the same vendor."))
        
        # Check if all requests are in approved state
        if any(pr.state != 'approved' for pr in self):
            raise UserError(_("Only approved purchase orders can be merged."))
        
        # Sort by date created and take the first one as main
        requests = self.sorted(key=lambda r: r.create_date)
        main_request = requests[0]
        requests_to_merge = requests[1:]

        # Move all lines to main request using write
        request_line_ids = requests_to_merge.mapped('request_line_ids')
        if request_line_ids:
            request_line_ids.write({'request_id': main_request.id})
        
        # Post message on main request about the merge
        merged_names = requests_to_merge.mapped('name')
        main_request.message_post(
            body=_("Merged with purchase requests: %s") % ", ".join(merged_names)
        )

        # Post messages on merged requests and cancel them
        for request in requests_to_merge:
            request.message_post(
                body=_("Merged into purchase request %s") % main_request.name
            )
            request.write({'state': 'cancelled'})

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.request',
            'res_id': main_request.id,
            'view_mode': 'form',
            'target': 'current',
        }
    

    # Create a purchase order from the request
    def action_create_po(self):
        self.ensure_one()

        if not self.partner_id:
            raise UserError(_("Please select a vendor before creating a purchase order. A vendor is required for purchase orders."))
        
        # log the job and job number for each line using the logger
        # for line in self.request_line_ids:
        #     _logger.info("Line %s: Job %s, Job Number %s", line.id, line.job, line.job_number)

        self.po_create_date = fields.Datetime.now()
            
        order_lines = []
        for line in self.request_line_ids:

            job_value = str(line.job.id) if line.job else 'Unknown'

            order_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.name,
                'product_qty': line.quantity,
                'product_uom': line.product_uom_id.id,
                'job': job_value,
                'job_number': line.job_number,
                'expense_type': line.expense_type,
                'price_unit': line.price_unit,
                'manufacturer': line.manufacturer,
                'manufacturernumber': line.manufacturer_number,
                'pop_start': line.pop_start,
                'pop_end': line.pop_end,
                'requestor_id': self.requester_id.id
            }))
            
        po_vals = {
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'order_line': order_lines,
            'date_planned': fields.Date.today() + relativedelta(days=self.longest_lead_time),
            'user_id': self.purchaser_id.id,
            'urgency': 'stoppage' if self.production_stoppage else False,
            'edge_recipient_new': self.deliver_to.id,
            'deliver_to_other': self.deliver_to_other,
            'deliver_to_other_address': self.deliver_to_other_address,
        }
        
        purchase_order = self.env['purchase.order'].create(po_vals)

        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'purchase.request'),
            ('res_id', '=', self.id)
        ])

        for attachment in attachments:
            attachment.copy({
                'res_model': 'purchase.order',
                'res_id': purchase_order.id,
                'name': attachment.name
            })

        self.write({
            'state': 'po_created',
            'purchase_order_id': purchase_order.id
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': purchase_order.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_cancel(self):
        return {
            'name': _('Confirm Cancellation'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.request.cancel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
            }
        }

    def action_draft(self):
        self.write({'state': 'draft'})
        for i in range(1, 13):
            setattr(self, f'is_level_{i}_approved', False)

    @api.model_create_multi
    def create(self, vals_list):

        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('purchase.request') or 'New'
        return super().create(vals_list)

    @api.depends('state')
    def _compute_can_approve(self):
        for record in self:
            # Get current user's email
            current_user_email = self.env.user.email
            
            # Define authorized alternate approvers who can approve at any level
            alternate_approver_emails = ['kweber@edgeautonomy.io', 'jcanale@edgeautonomy.io']
            
            # If current user is an authorized alternate, they can approve any request
            if current_user_email in alternate_approver_emails:
                record.can_approve = True
                continue
            
            # Otherwise, follow standard approval logic
            record.can_approve = False
            for i in range(1, 13):
                if getattr(record, f'needs_approver_level_{i}') and not getattr(record, f'is_level_{i}_approved'):
                    approver = getattr(record, f'approver_level_{i}')
                    if approver and approver.user_id == self.env.user:
                        record.can_approve = True
                    break