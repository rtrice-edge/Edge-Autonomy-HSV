from odoo import models, fields, api
import requests

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

    vendor_number = fields.Char(string='Jamis Vendor Number')

    # sam_uei = fields.Char(string='Unique Entity ID (SAM)')
    # sam_legal_business_name = fields.Char(string='Legal Business Name')
    
    # New additional fields
    # sam_entity_type_desc = fields.Char(string='Entity Type')
    # sam_organization_structure_desc = fields.Char(string='Organization Structure')
    # sam_sba_small_business = fields.Char(string='SBA Small Business')
    # sam_naics_description = fields.Text(string='NAICS Descriptions')

    # @api.model
    # def fetch_sam_data(self, city, legal_business_name):
    #     api_key = "leg9GidHyTvB9au7yOIZrRfGYAqfZK2UMlGXlag2"
    #     url = f"https://api.sam.gov/entity-information/v2/entities"
    #     params = {
    #         'api_key': api_key,
    #         'physicalAddressCity': city,
    #         'legalBusinessName': legal_business_name
    #     }
        
    #     try:
    #         response = requests.get(url, params=params)
    #         response.raise_for_status()
    #         data = response.json()
            
    #         if data['totalRecords'] > 0:
    #             entity = data['entityData'][0]
    #             registration = entity.get('entityRegistration', {})
    #             core_data = entity.get('coreData', {})
    #             assertions = entity.get('assertions', {})

    #             # Process NAICS information
    #             naics_list = assertions.get('goodsAndServices', {}).get('naicsList', [])
    #             naics_codes = []
    #             naics_descriptions = []
    #             sba_small_business = []
    #             for naics in naics_list:
    #                 naics_codes.append(naics.get('naicsCode'))
    #                 naics_descriptions.append(f"{naics.get('naicsCode')}: {naics.get('naicsDescription')}")
    #                 sba_small_business.append(f"{naics.get('naicsCode')}: {naics.get('sbaSmallBusiness', 'N/A')}")

    #             return {
    #                 'sam_uei': registration.get('ueiSAM'),
    #                 'sam_cage_code': registration.get('cageCode'),
    #                 'sam_legal_business_name': registration.get('legalBusinessName'),
    #                 'sam_dba_name': registration.get('dbaName'),
    #                 'sam_registration_status': registration.get('registrationStatus'),
    #                 'sam_entity_url': core_data.get('entityInformation', {}).get('entityURL'),
    #                 'sam_entity_division_name': core_data.get('entityInformation', {}).get('entityDivisionName'),
    #                 'sam_fiscal_year_end_close_date': core_data.get('entityInformation', {}).get('fiscalYearEndCloseDate'),
    #                 'sam_congressional_district': core_data.get('congressionalDistrict'),
    #                 'sam_business_types': ', '.join([bt.get('businessTypeDesc') for bt in core_data.get('businessTypes', {}).get('businessTypeList', [])]),
    #                 'sam_primary_naics': assertions.get('goodsAndServices', {}).get('primaryNaics'),
    #                 'sam_naics_codes': ', '.join(naics_codes),
    #                 'sam_credit_card_usage': core_data.get('financialInformation', {}).get('creditCardUsage'),
    #                 'sam_debt_subject_to_offset': core_data.get('financialInformation', {}).get('debtSubjectToOffset'),
    #                 'sam_disaster_registry_flag': assertions.get('disasterReliefData', {}).get('disasterRegistryFlag'),
    #                 'sam_entity_type_desc': core_data.get('generalInformation', {}).get('entityTypeDesc'),
    #                 'sam_organization_structure_desc': core_data.get('generalInformation', {}).get('organizationStructureDesc'),
    #                 'sam_sba_small_business': ', '.join(sba_small_business),
    #                 'sam_naics_description': '\n'.join(naics_descriptions),
    #             }
    #         else:
    #             return {}
    #     except Exception as e:
    #         _logger.error(f"Error fetching SAM data: {str(e)}")
    #         return {}

    # # @api.model
    # # def parse_date(self, date_string):
    # #     if date_string:
    # #         try:
    # #             return datetime.strptime(date_string, '%Y-%m-%d').date()
    # #         except ValueError:
    # #             return None
    # #     return None

    # @api.model
    # def create(self, vals):
    #     partner = super(ResPartner, self).create(vals)
    #     if partner.city and partner.name:
    #         sam_data = self.fetch_sam_data(partner.city, partner.name)
    #         partner.write(sam_data)
    #     return partner

    # def write(self, vals):
    #     res = super(ResPartner, self).write(vals)
    #     if 'city' in vals or 'name' in vals:
    #         for partner in self:
    #             sam_data = self.fetch_sam_data(partner.city, partner.name)
    #             super(ResPartner, partner).write(sam_data)
    #     return res

    #something went wrong.
    @api.depends('is_company')
    def _compute_vendor_number(self):
        for partner in self:
            if partner.is_company and isinstance(partner.id, int): # Check if vendor and `partner.id` is an integer
                partner.vendor_number = f'V{partner.id:06d}'
            else:
                partner.vendor_number = False