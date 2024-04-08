#odoo procurement category

from odoo import models, fields, api
class ProjectTable(models.Model):
    _name = 'project.table'
    _description = 'Project Table'

    name = fields.Char('Purchases')
    project_id = fields.Many2one('project.project', string='Project')
    # Add any other fields you need for your table

