#odoo procurement category

from odoo import models, fields, api

class Project(models.Model):
    _inherit = 'project.project'

    project_purchases = fields.One2many('project.table', 'project_id', string='Project Purchases')

