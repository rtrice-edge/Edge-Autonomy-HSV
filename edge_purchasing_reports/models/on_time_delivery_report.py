from odoo import models, fields, tools, api
from datetime import datetime, time, timedelta, date

class OnTimeDeliveryWizard(models.TransientModel):
    _name = 'on.time.delivery.wizard'
    _description = 'Select parameters for On-Time Delivery Report'

    # Default date_start to one year ago from today
    def _default_date_start(self):
        return date.today() - timedelta(days=365)

    # Default date_end to today
    def _default_date_end(self):
        return date.today()

    date_start = fields.Date(string='Start Date', required=True, default=_default_date_start)
    date_end = fields.Date(string='End Date', required=True, default=_default_date_end, 
                         help="End date is inclusive")
    production_items_only = fields.Boolean(
        string='Production Items Only', 
        default=False,
        help="Show only items where Job is 'Inventory (Raw Materials)'"
    )
    
    # New field for grouping selection
    group_by = fields.Selection([
        ('vendor', 'Vendor'),
        ('month', 'Month'),
        ('week', 'Week')
    ], string='Group By', default='vendor', required=True)

    def action_open_report(self):
        domain = []
        
        if self.date_start:
            # Convert date to datetime string at start of day
            start_datetime = datetime.combine(self.date_start, time.min)
            domain.append(('effective_date', '>=', fields.Datetime.to_string(start_datetime)))
        if self.date_end:
            # Convert date to datetime string at end of day
            end_datetime = datetime.combine(self.date_end, time.max)
            domain.append(('effective_date', '<=', fields.Datetime.to_string(end_datetime)))
            
        if self.production_items_only:
            domain.append(('job', '=', 'Inventory (Raw Materials)'))
            
        # Define context based on the selected grouping option
        context = {
            'pivot_measures': ['on_time_rate', 'delivery_line_count', 'on_time_delivery_count'],
            'pivot_column_groupby': [],
        }
        
        # Configure row groupings based on selected option
        if self.group_by == 'vendor':
            context['pivot_row_groupby'] = ['partner_name']
            context['search_default_groupby_partner'] = 1
        elif self.group_by == 'month':
            context['pivot_row_groupby'] = ['effective_date:month']
            context['search_default_groupby_effective_date_month'] = 1
        elif self.group_by == 'week':
            context['pivot_row_groupby'] = ['effective_date:month', 'effective_date:week']
            context['search_default_groupby_effective_date_month'] = 1
            context['search_default_groupby_effective_date_week'] = 1
            
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vendor On-Time Delivery Performance',
            'res_model': 'on.time.delivery.report',
            'view_mode': 'pivot,tree,graph',
            'domain': domain,
            'context': context,
        }