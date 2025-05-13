from odoo import models, fields, api, _
from datetime import datetime, time, timedelta
from dateutil.relativedelta import relativedelta

class OnTimeDeliveryViewSelector(models.TransientModel):
    _name = 'on.time.delivery.view.selector'
    _description = 'On-Time Delivery View Selector'

    view_type = fields.Selection([
        ('vendor_specific', 'Vendor Specific'),
        ('monthly', 'All Vendors by Month'),
        ('weekly', 'All Vendors by Week')
    ], string='View Type', required=True, default='vendor_specific')

    def action_open_selected_view(self):
        """Open the selected report view based on user choice"""
        self.ensure_one()
        
        if self.view_type == 'vendor_specific':
            # Open the existing wizard for vendor-specific view
            return {
                'type': 'ir.actions.act_window',
                'name': _('Vendor On-Time Delivery Parameters'),
                'res_model': 'on.time.delivery.wizard',
                'view_mode': 'form',
                'target': 'new',
                'view_id': self.env.ref('vendor_on_time_delivery.view_on_time_delivery_wizard').id,
            }
        
        elif self.view_type in ['monthly', 'weekly']:
            # For time-based views, calculate default date range
            today = fields.Date.today()
            date_end = today
            
            if self.view_type == 'monthly':
                # Last 12 months by default
                date_start = today + relativedelta(months=-12)
                groupby = 'effective_date:month'
            else:  # weekly
                # Last 12 weeks by default
                date_start = today + relativedelta(weeks=-52)
                groupby = 'effective_date:week'
            
            domain = [
                ('effective_date', '>=', fields.Datetime.to_string(datetime.combine(date_start, time.min))),
                ('effective_date', '<=', fields.Datetime.to_string(datetime.combine(date_end, time.max)))
            ]
            
            return {
                'type': 'ir.actions.act_window',
                'name': _('On-Time Delivery Performance by Time'),
                'res_model': 'on.time.delivery.report',
                'view_mode': 'pivot,graph',
                'domain': domain,
                'context': {
                    'pivot_measures': ['on_time_rate', 'delivery_line_count', 'on_time_delivery_count'],
                    'pivot_row_groupby': [groupby],
                    'pivot_column_groupby': [],
                    'graph_groupbys': [groupby],
                    'graph_measure': 'on_time_rate'
                },
            }
        
        return {'type': 'ir.actions.act_window_close'}