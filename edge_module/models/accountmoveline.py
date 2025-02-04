from odoo import models, fields, api

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    job_number = fields.Char(string='Job Number', readonly=True, store=True)
    expense_type = fields.Selection([
        ('Unknown', 'Unknown'),
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
    ], string='Expense Type', default='Unknown', readonly=True)