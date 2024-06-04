from odoo import fields, models

class QualityCheck(models.Model):
    _inherit = 'quality.check'

    worksheet_document = fields.Binary(related='point_id.worksheet_document', readonly=True)
