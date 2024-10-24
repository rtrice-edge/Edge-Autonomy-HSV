from odoo import models, fields, api, tools
import math
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class AccountMapping(models.Model):
    _name = 'account.mapping'
    _description = 'Account Mapping'

    expense_type = fields.Char(string='Cost Element', required=True)
    cost_objective = fields.Char(string='Job', required=False)

    _sql_constraints = [
        ('expense_type_cost_objective_unique', 'unique(expense_type, cost_objective)', 'The combination of Expense Type and Cost Objective must be unique.')
    ]
    
    