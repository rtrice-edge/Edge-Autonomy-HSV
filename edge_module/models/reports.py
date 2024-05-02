from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, get_lang



import logging
_logger = logging.getLogger(__name__)



class PurchaseOrderReport(models.AbstractModel):
    _inherit = 'purchase.report_purchaseorder_document'

    def _get_rendering_context(self, docids, data):
        rendering_context = super()._get_rendering_context(docids, data)
        rendering_context['report_context']['font_family'] = 'Arial'
        rendering_context['report_context']['font_size'] = '8px'
        return rendering_context