from odoo import models, fields, tools, api
from datetime import datetime, time, timedelta, date

class OnTimeDeliveryReport(models.Model):
    _name = 'on.time.delivery.report'
    _description = 'Vendor On-Time Delivery Performance Report'
    _auto = False
    # _order removed as global on-time percentage is no longer a direct field
    # Consider setting a default order in the action or view if needed e.g., 'effective_date desc'

    # --- Fields for individual delivery lines ---
    partner_id = fields.Many2one('res.partner', string='Vendor', readonly=True)
    partner_name = fields.Char(string='Vendor', readonly=True)
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order', readonly=True)
    purchase_order_name = fields.Char(string='PO Reference', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_name = fields.Char(string='Product', readonly=True)
    job = fields.Char(string='Job', readonly=True) # Used for "Production Items Only" filter
    expense_type = fields.Char(string='Expense Type', readonly=True) # Added expense_type field
    product_qty = fields.Float(string='Quantity', readonly=True)
    date_planned = fields.Datetime(string='Expected Delivery', readonly=True)
    effective_date = fields.Datetime(string='Latest Delivery', readonly=True)
    is_on_time = fields.Boolean(string='Is On Time', readonly=True)
    is_late = fields.Boolean(string='Is Late', readonly=True)
    days_late = fields.Integer(string='Days Late', readonly=True)
    pol_id = fields.Integer(string='Purchase Order Line ID', readonly=True) # Storing POL ID

    # --- Fields for dynamic aggregation by Odoo views (e.g., Pivot) ---
    # This field will be 1.0 if on_time, 0.0 if not. Averaging it gives the on-time percentage.
    on_time_rate = fields.Float(string='On-Time Rate', readonly=True, group_operator='avg')
    
    # This field will be 1 for every line. Summing it gives the total number of deliveries.
    delivery_line_count = fields.Integer(string='Total Deliveries Count', readonly=True, group_operator='sum')
    
    # This field will be 1 if on_time, 0 if not. Summing it gives the total on-time deliveries.
    on_time_delivery_count = fields.Integer(string='On-Time Deliveries Count', readonly=True, group_operator='sum')


    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table) # Use self._table for view name
        self.env.cr.execute("""
        CREATE OR REPLACE VIEW {} AS (
            WITH delivery_stats AS (
                SELECT
                    pol.id AS pol_id,
                    po.partner_id,
                    rp.name AS partner_name,
                    po.id AS purchase_order_id,
                    po.name AS purchase_order_name,
                    pol.product_id,
                    (pt.name::json ->> 'en_US') AS product_name, -- Assuming product name is translatable
                    CASE
                        WHEN j.name IS NOT NULL THEN j.name
                        WHEN pol.job = 'Unknown' OR pol.job IS NULL THEN 'Unknown'
                        -- Consider if pol.job could hold other values that should be displayed
                        ELSE COALESCE(pol.job, 'Unknown') 
                    END AS job,
                    CASE
                        WHEN pol.expense_type = 'raw_materials' THEN 'Inventory (Raw Materials)'
                        WHEN pol.expense_type = 'subcontractors' THEN 'Subcontractors/Consultants/Outside Professionals'
                        WHEN pol.expense_type = 'consumables' THEN 'Consumables'
                        WHEN pol.expense_type = 'small_tooling' THEN 'Small Tooling'
                        WHEN pol.expense_type = 'manufacturing_supplies' THEN 'Manufacturing Supplies'
                        WHEN pol.expense_type = 'engineering_supplies' THEN 'Engineering Supplies'
                        WHEN pol.expense_type = 'office_supplies' THEN 'Office Supplies'
                        WHEN pol.expense_type = 'building_supplies' THEN 'Facilities - Building Supplies'
                        WHEN pol.expense_type = 'janitorial' THEN 'Facilities - Janitorial'
                        WHEN pol.expense_type = 'communications' THEN 'Facilities - Phones/Internet/Communications'
                        WHEN pol.expense_type = 'utilities' THEN 'Facilities - Utilities & Waste'
                        WHEN pol.expense_type = 'flight_ops' THEN 'Flight Ops Materials & Supplies'
                        WHEN pol.expense_type = 'it_hardware' THEN 'IT Hardware'
                        WHEN pol.expense_type = 'it_software' THEN 'IT Software'
                        WHEN pol.expense_type = 'it_services' THEN 'IT Services'
                        WHEN pol.expense_type = 'repairs' THEN 'Repairs & Maintenance'
                        WHEN pol.expense_type = 'business_dev' THEN 'Business Development Expenses'
                        WHEN pol.expense_type = 'training' THEN 'Conference/Seminar/Training Fees'
                        WHEN pol.expense_type = 'licenses' THEN 'Licenses & Permits'
                        WHEN pol.expense_type = 'vehicle' THEN 'Vehicle Supplies'
                        WHEN pol.expense_type = 'equipment_rental' THEN 'Equipment Rental'
                        WHEN pol.expense_type = 'employee_morale' THEN 'Employee Morale Costs'
                        WHEN pol.expense_type = 'safety' THEN 'Safety Supplies'
                        WHEN pol.expense_type = 'marketing' THEN 'Marketing Expenses'
                        WHEN pol.expense_type = 'recruiting' THEN 'Recruiting Costs'
                        WHEN pol.expense_type = 'shipping' THEN 'Shipping & Freight, Packaging Supplies'
                        WHEN pol.expense_type = 'direct_award' THEN 'Direct Award Materials (Cost of Good Sold)'
                        WHEN pol.expense_type = 'capex' THEN 'Capital Expenditures, non-IR&D (>$2,500)'
                        WHEN pol.expense_type = 'Unknown' THEN 'Unknown'
                        ELSE COALESCE(pol.expense_type, 'Unknown')
                    END AS expense_type, -- Map expense_type code to human-readable value
                    pol.product_qty,
                    pol.date_planned,
                    pol.effective_date,
                    CASE 
                        WHEN pol.effective_date IS NULL THEN false
                        -- Grace period of 7 days for on-time delivery
                        WHEN pol.effective_date <= (pol.date_planned + interval '7 days') THEN true
                        ELSE false
                    END AS is_on_time,
                    CASE 
                        WHEN pol.effective_date IS NULL THEN false
                        WHEN pol.effective_date > (pol.date_planned + interval '7 days') THEN true
                        ELSE false
                    END AS is_late,
                    CASE
                        WHEN pol.effective_date IS NULL THEN 0
                        WHEN pol.effective_date > pol.date_planned THEN 
                            EXTRACT(DAY FROM (pol.effective_date - pol.date_planned))::integer
                        ELSE 0
                    END AS days_late
                FROM
                    purchase_order_line pol
                JOIN
                    purchase_order po ON pol.order_id = po.id
                JOIN
                    res_partner rp ON po.partner_id = rp.id
                LEFT JOIN
                    product_product pp ON pol.product_id = pp.id
                LEFT JOIN
                    product_template pt ON pp.product_tmpl_id = pt.id
                LEFT JOIN
                    job j ON pol.job = CAST(j.id AS varchar) -- Ensure this join logic for 'job' is correct for your setup
                WHERE
                    pol.display_type IS NULL
                    AND po.state IN ('purchase', 'done')
                    AND pol.effective_date IS NOT NULL -- Only consider lines with an effective delivery date
            )
            SELECT
                ROW_NUMBER() OVER () AS id, -- Mandatory unique ID for the view
                ds.pol_id, -- Retain original POL ID if needed for drill-down or reference
                ds.partner_id,
                ds.partner_name,
                ds.purchase_order_id,
                ds.purchase_order_name,
                ds.product_id,
                ds.product_name,
                ds.job,
                ds.expense_type, -- Added expense_type to the final SELECT
                ds.product_qty,
                ds.date_planned,
                ds.effective_date,
                ds.is_on_time,
                ds.is_late,
                ds.days_late,
                -- Fields for aggregation
                CASE WHEN ds.is_on_time THEN 1.0 ELSE 0.0 END AS on_time_rate,
                1 AS delivery_line_count,
                CASE WHEN ds.is_on_time THEN 1 ELSE 0 END AS on_time_delivery_count
            FROM
                delivery_stats ds
        )
        """.format(self._table))

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
        help="Show only items where Job is 'Inventory (Raw Materials)' or expense type is 'Inventory (Raw Materials)'"
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
            # Modified to include both job and expense_type for production items
            domain.append('|')
            domain.append(('job', '=', 'Inventory (Raw Materials)'))
            domain.append(('expense_type', '=', 'Inventory (Raw Materials)'))
            
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
            context['pivot_row_groupby'] = ['effective_date:week']
            context['search_default_groupby_effective_date_week'] = 1
            
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vendor On-Time Delivery Performance',
            'res_model': 'on.time.delivery.report',
            'view_mode': 'pivot,tree,graph',
            'domain': domain,
            'context': context,
        }