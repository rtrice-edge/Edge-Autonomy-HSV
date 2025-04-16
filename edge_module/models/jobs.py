from odoo import models, fields, api

class Jobs(models.Model):
    _name = 'job'
    _description = 'Jobs Management'
    _order = 'name'
    
    name = fields.Char(string='Job Name', required=True)
    number = fields.Char(string='Job Number', required=True)
    active = fields.Boolean(default=True)
    
    _sql_constraints = [
        ('unique_job_number', 'unique(number)', 'Job Number must be unique!')
    ]