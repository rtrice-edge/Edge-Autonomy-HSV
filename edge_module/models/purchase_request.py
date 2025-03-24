from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import format_date
from dateutil.relativedelta import relativedelta
from odoo.tools.misc import clean_context
# from .TeamsLib import TeamsLib

import logging
_logger = logging.getLogger(__name__)

class PurchaseRequest(models.Model):
    _name = 'purchase.request'
    _description = 'Purchase Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char('Request Number', readonly=True, default='New', copy=False)
    partner_id = fields.Many2one('res.partner', string='Suggested Vendor', tracking=True,
                                domain="[('supplier_rank', '>', 0)]", required=False)
    currency_id = fields.Many2one('res.currency', string='Currency', 
                                 default=lambda self: self.env.company.currency_id.id)
    request_line_ids = fields.One2many('purchase.request.line', 'request_id', 
                                      string='Request Lines')
    urgency = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('production_stoppage', 'Production Stoppage')
    ], string='Urgency', required=True, default='low', 
    help="""Low: No production impact.

            Medium: Mostly expense items non-production item, production items.

            High: Production items with production impact.

            Production Stoppage: An urgent production stoppage (if we do not get an item quickly it will have an impact on our production ability) or an urgent item needed to support our customer.""")
    date_requested = fields.Date('Date Requested', 
                                default=fields.Date.context_today, readonly=True)
    requester_id = fields.Many2one('res.users', string='Requester', 
                                  default=lambda self: self.env.user.id, readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending_validation', 'Pending Validation'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('po_created', 'PO Created'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    company_id = fields.Many2one('res.company', string='Company', 
                                default=lambda self: self.env.company)
    amount_total = fields.Monetary(string='Total', compute='_compute_amount_total',
                                 store=True, currency_field='currency_id')
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order',
                                       readonly=True, copy=False)
    deliver_to = fields.Many2one('res.users', string='Internal Recipient', required=False, tracking=True)
    deliver_to_address = fields.Selection([
        ('edge_slo', 'Edge Autonomy HSV'),
        ('other', 'Other')
    ], string='Final Destination', default='edge_slo', required=True, tracking=True,
    help="Only select 'Other' if the items will be received at Edge Autonomy and then shipped out to someone specific at another location.")
    deliver_to_other = fields.Char('External Recipient', tracking=True)
    deliver_to_other_address = fields.Char('Final Destination Address', tracking=True)
    needs_other_delivery = fields.Boolean(compute='_compute_needs_other_delivery', default=False, store=True)
    requester_notes = fields.Text('Requester Notes', tracking=True, help="Anything relevant to purchase request: detailed info, links, special notes etc.")
    need_by_date = fields.Date('Need by Date', required=True)
    purchaser_id = fields.Many2one('res.users', string='Purchaser', tracking=True, 
                              domain=lambda self: [('groups_id', 'in', [self.env.ref('purchase.group_purchase_manager').id])],
                              default=lambda self: self.env['res.users'].search([('email', '=', 'bmccoy@edgeautonomy.io')], limit=1).id)
    
    # resale_designation = fields.Selection([
    #     'resale', 'For Resale',
    #     'no_resale', 'Not For Resale'
    # ], string='Resale Designation', required=True)
    
    approver_id = fields.Many2one(
        'purchase.request.approver', 
        string='Approver',
        tracking=True
    )

    can_approve = fields.Boolean(compute='_compute_can_approve', store=False)

    is_dept_mgr_approved = fields.Boolean(default=False)
    is_prog_mgr_approved = fields.Boolean(default=False)
    is_sc_mgr_approved = fields.Boolean(default=False)
    is_gm_coo_approved = fields.Boolean(default=False)
    is_exec_approved = fields.Boolean(default=False)
    
    approver_level_1 = fields.Many2one(
        'purchase.request.approver', 
        string='Dept Manager Approver',
        tracking=True,
        ondelete='restrict',
        domain="[('manager_level', '=', 'dept_mgr')]",
        help="Department Manager who will approve this request"
    )

    needs_approver_level_1 = fields.Boolean(
        compute='_compute_approvers_needed', default=False, store=True
    )

    approver_level_2 = fields.Many2one(
        'purchase.request.approver',
        string='Program Manager Approver', 
        tracking=True,
        ondelete='restrict',
        domain="[('manager_level', '=', 'prog_mgr')]",
        help="Program Manager who will approve this request"
    )

    needs_approver_level_2 = fields.Boolean(
        compute='_compute_approvers_needed', default=False, store=True
    )

    approver_level_3 = fields.Many2one(
        'purchase.request.approver',
        string='Supply Chain Manager Approver',
        tracking=True, 
        ondelete='restrict',
        domain="[('manager_level', '=', 'sc_mgr')]",
        help="Supply Chain Manager who will approve this request"
    )

    needs_approver_level_3 = fields.Boolean(
        compute='_compute_approvers_needed', default=False, store=True
    )

    approver_level_4 = fields.Many2one(
        'purchase.request.approver',
        string='GM/COO Approver',
        tracking=True,
        ondelete='restrict',
        domain="[('manager_level', '=', 'gm_coo')]",
        help="GM/COO who will approve this request"
    )

    needs_approver_level_4 = fields.Boolean(
        compute='_compute_approvers_needed', default=False, store=True
    )

    approver_level_5 = fields.Many2one(
        'purchase.request.approver',
        string='Executive Approver',
        tracking=True,
        ondelete='restrict',
        domain="[('manager_level', '=', 'exec')]",
        help="Executive who will approve this request"
    )

    needs_approver_level_5 = fields.Boolean(
        compute='_compute_approvers_needed', default=False, store=True
    )


    # TESTING TEAMS NOTIFICATIONS
    # @api.onchange('approver_level_1')
    # def send_teams_message_test(self):
    #     if not self.approver_level_1 or not self.needs_approver_level_1:
    #         return

    #     try:
    #         teams_lib = TeamsLib()
            
    #         # Get the user's email from the approver record
    #         approver_email = self.approver_level_1.user_id.email
    #         if not approver_email:
    #             _logger.error(f"No email found for approver: {self.approver_level_1.name}")
    #             return

    #         # Get Teams user ID
    #         teams_user_id = teams_lib.get_user_id(approver_email)
    #         if not teams_user_id:
    #             _logger.error(f"Could not find Teams user ID for email: {approver_email}")
    #             return

    #         # Construct message
    #         message = f"""
    # You have been assigned as Level 1 Approver for {self.name}
    # Request details:
    # - Requester: {self.requester_id.name}
    # - Total Amount: {self.company_id.currency_id.symbol}{self.amount_total:,.2f}
    # - Urgency: {dict(self._fields['urgency'].selection).get(self.urgency)}
    # """
    #         # Send message
    #         teams_lib.send_message(teams_user_id, message)
            
    #     except Exception as e:
    #         _logger.error(f"Failed to send Teams notification: {str(e)}", exc_info=True)

    @api.depends('deliver_to_address')
    def _compute_needs_other_delivery(self):
        for record in self:
            if record.deliver_to_address == 'other':
                self.needs_other_delivery = True
            else:
                self.needs_other_delivery = False

    # @api.depends('request_line_ids.job', 'request_line_ids.expense_type')
    # def _compute_(self):
    #     for record in self:
    #         if record.request_line_ids.job == 'Inventory (Raw Materials)' or record.request_line_ids.expense_type == 'raw_materials':
    #             self.resale_designation = 'resale'
    #         else:
    #             self.resale_designation = 'no_resale'

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
                for level in range(1, 6):
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

                # A mapping between manager_level and our level numbers.
                level_map = {
                    'dept_mgr': 1,
                    'prog_mgr': 2,
                    'sc_mgr': 3,
                    'gm_coo': 4,
                    'exec': 5,
                }

                has_approver = False

                # If the total amount is above 10,000, set level 3 approval.
                # if request.amount_total > 10000:
                #     request.needs_approver_level_3 = True
                #     has_approver = True

                # _logger.info("Found %s approval matrix rules", len(approval_matrix_rules))
                # approval_matrix_rules_job_texts = approval_matrix_rules.mapped('job_text')
                # approval_matrix_rules_job_ids = approval_matrix_rules.mapped('job_id')
                # _logger.info("Approval Matrix Rules Job Texts: %s", approval_matrix_rules_job_texts)
                # _logger.info("Approval Matrix Rules Job IDs: %s", approval_matrix_rules_job_ids)
                # Process each approval matrix rule.
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
                        if rule.first_approver_level:
                            level_num = level_map.get(rule.first_approver_level)
                            if level_num:
                                setattr(request, f'needs_approver_level_{level_num}', True)
                                has_approver = True
                        if rule.second_approver_level:
                            level_num = level_map.get(rule.second_approver_level)
                            if level_num:
                                setattr(request, f'needs_approver_level_{level_num}', True)
                                has_approver = True
                        if rule.third_approver_level:
                            level_num = level_map.get(rule.third_approver_level)
                            if level_num:
                                setattr(request, f'needs_approver_level_{level_num}', True)
                                has_approver = True

                # _logger.info("Has approver: %s", has_approver)
                # If no rules set any approver level, then default to level 1.
                if not has_approver:
                    request.needs_approver_level_1 = True
        

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
        help="Only required if requesting services")

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
    
    # for all the needs_approval_level_x fields that are true, if all the corresponding is_x_approved fields are true, then the request is fully approved
    def is_fully_approved(self):
        for record in self:
            if record.needs_approver_level_1 and not record.is_dept_mgr_approved:
                return False
            if record.needs_approver_level_2 and not record.is_prog_mgr_approved:
                return False
            if record.needs_approver_level_3 and not record.is_sc_mgr_approved:
                return False
            if record.needs_approver_level_4 and not record.is_gm_coo_approved:
                return False
            if record.needs_approver_level_5 and not record.is_exec_approved:
                return False
        return True


    def action_submit(self):
        if not self.request_line_ids:
            raise UserError(_("You cannot submit a purchase request with no request lines."))
        if self.amount_total <= 0:
            raise UserError(_("You cannot submit a purchase request with a total amount of $0."))

        self.write({'state': 'pending_validation'})

    def action_validate(self):
        self.write({'state': 'pending_approval'})
        self._notify_next_approver()

        # return {
        #     'type': 'ir.actions.client',
        #     'tag': 'reload',
        #     'params': {
        #         'type': 'notification',
        #         'title': 'Validated',
        #         'message': 'An email has been sent to notify the first approver.',
        #         'sticky': False,
        #         'next': {'type': 'ir.actions.client', 'tag': 'reload'},  
        #     }
        # }


    def _notify_next_approver(self):

        recipient = False

        if self.needs_approver_level_1 and not self.is_dept_mgr_approved:
            recipient = self.approver_level_1
        elif self.needs_approver_level_2 and not self.is_prog_mgr_approved:
            recipient = self.approver_level_2
        elif self.needs_approver_level_3 and not self.is_sc_mgr_approved:
            recipient = self.approver_level_3
        elif self.needs_approver_level_4 and not self.is_gm_coo_approved:
            recipient = self.approver_level_4
        elif self.needs_approver_level_5 and not self.is_exec_approved:
            recipient = self.approver_level_5

        if recipient and recipient.user_id.partner_id:

            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = f"{base_url}/web#id={self.id}&view_type=form&model={self._name}"

            body_html = f"""
                <p>{recipient.user_id.name},</p>
                <p>{self.name} requires your approval</p>
                <br/>
                <p><strong>Details:</strong></p>
                <ul>
                    <li>Requester: {self.requester_id.name}</li>
                    <li>Total Amount: {self.currency_id.symbol} {self.amount_total:,.2f}</li>
                    <li>Urgency: {dict(self._fields['urgency'].selection).get(self.urgency)}</li>
                    <li>Need by Date: {self.need_by_date}</li>
                </ul>
                <br/>
                <div style="margin: 16px 0px 16px 0px;">
                    <a href="{url}" 
                    style="background-color: #875A7B; padding: 8px 16px 8px 16px; 
                            text-decoration: none; color: #fff; border-radius: 5px; 
                            font-size:13px;">
                        View Purchase Request
                    </a>
                </div>
                <br/>
                <p>Best regards,<br/>
                Edge Autonomy Procurement</p>
            """

            # Subscribe the approver
            # self.message_subscribe(partner_ids=[recipient.user_id.partner_id.id])

            # Create and send email
            mail_values = {
                'email_from': self.env.user.partner_id.email,
                'author_id': self.env.user.partner_id.id,
                'model': self._name,
                'res_id': self.id,
                'subject': f'Approval Required: {self.name}',
                'body_html': body_html,
                'email_to': recipient.user_id.partner_id.email,
                'auto_delete': True,
            }
            
            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.send()
            
            _logger.info("Email created and sent: %s", mail.id if mail else 'No mail created')


    def action_approve(self):
        if self.needs_approver_level_1 and not self.is_dept_mgr_approved:
            self.write({
                'is_dept_mgr_approved': True
            })
        elif self.needs_approver_level_2 and not self.is_prog_mgr_approved:
            self.write({
                'is_prog_mgr_approved': True
            })
        elif self.needs_approver_level_3 and not self.is_sc_mgr_approved:
            self.write({
                'is_sc_mgr_approved': True
            })
        elif self.needs_approver_level_4 and not self.is_gm_coo_approved:
            self.write({
                'is_gm_coo_approved': True
            })
        elif self.needs_approver_level_5 and not self.is_exec_approved:
            self.write({
                'is_exec_approved': True
            })
        else:
            raise UserError(_("Invalid state change."))
        
        # Post chatter message about approval
        self.message_post(
            body="Request approved.",
            message_type='notification',
            subtype_xmlid='mail.mt_comment'
        )
        
        if self.is_fully_approved():
            self.write({'state': 'approved'})
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
            
        order_lines = []
        for line in self.request_line_ids:
            order_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.name,
                'product_qty': line.quantity,
                'product_uom': line.product_uom_id.id,
                'job': line.job.id,
                'job_number': line.job_number,
                'expense_type': line.expense_type,
                'price_unit': line.price_unit,
                'manufacturer': line.manufacturer,
                'manufacturer_number': line.manufacturer_number,
                'pop_start': line.pop_start,
                'pop_end': line.pop_end,
            }))
            
        po_vals = {
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'order_line': order_lines,
            'date_planned': fields.Date.today() + relativedelta(days=self.longest_lead_time),
            'user_id': self.purchaser_id.id,
            'urgency': self.urgency,
            'edge_recipient_new': self.deliver_to.id,
            'deliver_to_other': self.deliver_to_other,
            'deliver_to_other_address': self.deliver_to_other_address,
        }
        
        purchase_order = self.env['purchase.order'].create(po_vals)
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
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self.write({'state': 'draft'})

    @api.model_create_multi
    def create(self, vals_list):

        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('purchase.request') or 'New'
        return super().create(vals_list)
    
    @api.depends('state')
    def _compute_can_approve(self):
        # is_manager = self.env.user.has_group('purchase.group_purchase_manager')
        # for record in self:
        #     if record.needs_approver_level_1 and not record.is_dept_mgr_approved:
        #         record.can_approve = (
        #             is_manager or 
        #             (record.approver_level_1 and record.approver_level_1.user_id == self.env.user)
        #         )
        for record in self:
            if record.needs_approver_level_1 and not record.is_dept_mgr_approved:
                record.can_approve = (record.approver_level_1 and record.approver_level_1.user_id == self.env.user)
            elif record.needs_approver_level_2 and not record.is_prog_mgr_approved:
                record.can_approve = (record.approver_level_2 and record.approver_level_2.user_id == self.env.user)
            elif record.needs_approver_level_3 and not record.is_sc_mgr_approved:
                record.can_approve = (record.approver_level_3 and record.approver_level_3.user_id == self.env.user)
            elif record.needs_approver_level_4 and not record.is_gm_coo_approved:
                record.can_approve = (record.approver_level_4 and record.approver_level_4.user_id == self.env.user)
            elif record.needs_approver_level_5 and not record.is_exec_approved:
                record.can_approve = (record.approver_level_5 and record.approver_level_5.user_id == self.env.user)
            else:
                record.can_approve = False
