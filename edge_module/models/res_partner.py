from odoo import models, fields, api

import logging
_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    vendor_terms = fields.Char(string='Vendor Terms')


    small_business_concern = fields.Boolean(string="Small Business Concern")
    nonprofit_organization = fields.Boolean(string="Nonprofit Organization")
    green_business = fields.Boolean(string="Green Business")
    woman_owned = fields.Boolean(string="Woman-Owned")
    home_business = fields.Boolean(string="Home Business")
    minority_owned = fields.Boolean(string="Minority Owned")
    university_college = fields.Boolean(string="University/College")
    small_disadvantaged_business = fields.Boolean(string="Small Disadvantaged Business")
    historically_black_college = fields.Boolean(string="Historically Black College")
    anc_native_american_non_small_business = fields.Boolean(string="ANC/Native American Non-Small Business")
    foreign_entity = fields.Boolean(string="Foreign Entity")
    large_business_concern = fields.Boolean(string="Large Business Concern")
    self_employed = fields.Boolean(string="Self-Employed")
    startup = fields.Boolean(string="Startup")
    online_business = fields.Boolean(string="Online Business")
    people_with_disabilities = fields.Boolean(string="People with Disabilities")
    veteran_owned = fields.Boolean(string="Veteran Owned")
    hubzone = fields.Boolean(string="HUBZone")
    service_disabled_veteran_owned = fields.Boolean(string="Service-Disabled Veteran Owned")
    anc_native_american_small_business = fields.Boolean(string="ANC/Native American Small Business")
    small_business_certified_by_sba = fields.Boolean(string="Small Business Certified by SBA")

    vendor_number = fields.Char(string='Vendor Number', compute='_compute_vendor_number', store=True)

    @api.depends('supplier_rank')
    def _compute_vendor_number(self):
        for partner in self:
            if partner.supplier_rank > 0:  # Check if the partner is a vendor
                partner.vendor_number = f'V{partner.id:06d}'
            else:
                partner.vendor_number = False

    def _generate_vendor_number(self):
        if not self.vendor_number:
            self.vendor_number = f'V{self.id:06d}'

    @api.model
    def _generate_missing_vendor_numbers(self):
        vendors_without_number = self.search([('is_company', '=', True)])
        for vendor in vendors_without_number:
            vendor._generate_vendor_number()
        _logger.info(f"Generated vendor numbers for {len(vendors_without_number)} vendors.")

    def init(self):
        # This method is called when the module is installed or updated
        self._generate_missing_vendor_numbers()