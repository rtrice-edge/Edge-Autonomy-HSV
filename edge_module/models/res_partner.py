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



    sam_uei = fields.Char(string="SAM UEI")
    legal_business_name = fields.Char(string="Legal Business Name")
    uei_status = fields.Char(string="UEI Status")
    uei_creation_date = fields.Date(string="UEI Creation Date")
    entity_url = fields.Char(string="Entity URL")
    entity_start_date = fields.Date(string="Entity Start Date")
    entity_structure_desc = fields.Char(string="Entity Structure Description")
    
    # Physical address fields
    physical_address_line1 = fields.Char(string="Address Line 1")
    physical_address_line2 = fields.Char(string="Address Line 2")
    physical_city = fields.Char(string="City")
    physical_state_or_province = fields.Char(string="State/Province")
    physical_zip_code = fields.Char(string="ZIP Code")
    physical_zip_plus4 = fields.Char(string="ZIP Code Plus 4")
    physical_country_code = fields.Char(string="Country Code")

    # Business type list fields (storing as text; you can modify based on your need)
    business_type_list = fields.Text(string="Business Types")

    credit_card_usage = fields.Char(string="Credit Card Usage")
    debt_subject_to_offset = fields.Char(string="Debt Subject to Offset")
    psc_description = fields.Text(string="PSC Description")
    
    # Points of contact
    gov_business_poc_first_name = fields.Char(string="Government Business POC First Name")
    gov_business_poc_last_name = fields.Char(string="Government Business POC Last Name")

    @api.model
    def fetch_sam_data(self, vendor_name, city):
        base_url = "https://api.sam.gov/entity-information/v2/entities"
        params = {
            "api_key": 'leg9GidHyTvB9au7yOIZrRfGYAqfZK2UMlGXlag2',
            "legalBusinessName": vendor_name,
        }

        # Include the city parameter only if it is present
        if city:
            params["city"] = city

        response = requests.get(base_url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            if data['totalRecords'] > 0:
                entity_data = data['entityData'][0]
                registration = entity_data['entityRegistration']
                core_data = entity_data['coreData']
                physical_address = core_data['physicalAddress']
                business_types = core_data['businessTypes']['businessTypeList']
                government_poc = entity_data['pointsOfContact']['governmentBusinessPOC']

                # Update fields based on API response
                self.sam_uei = registration.get('ueiSAM')
                self.legal_business_name = registration.get('legalBusinessName')
                self.uei_status = registration.get('ueiStatus')
                self.uei_creation_date = registration.get('ueiCreationDate')
                self.entity_url = core_data['entityInformation'].get('entityURL')
                self.entity_start_date = core_data['entityInformation'].get('entityStartDate')
                self.entity_structure_desc = core_data['generalInformation'].get('entityStructureDesc')

                # Physical address fields
                self.physical_address_line1 = physical_address.get('addressLine1')
                self.physical_address_line2 = physical_address.get('addressLine2')
                self.physical_city = physical_address.get('city')
                self.physical_state_or_province = physical_address.get('stateOrProvinceCode')
                self.physical_zip_code = physical_address.get('zipCode')
                self.physical_zip_plus4 = physical_address.get('zipCodePlus4')
                self.physical_country_code = physical_address.get('countryCode')

                # Business types
                self.business_type_list = ', '.join([bt['businessTypeDesc'] for bt in business_types])

                # Financial Information
                financial_info = core_data.get('financialInformation', {})
                self.credit_card_usage = financial_info.get('creditCardUsage')
                self.debt_subject_to_offset = financial_info.get('debtSubjectToOffset')

                # PSC description
                psc_list = entity_data['assertions']['goodsAndServices']['pscList']
                self.psc_description = ', '.join([psc['pscDescription'] for psc in psc_list])

                # Government Business POC
                self.gov_business_poc_first_name = government_poc.get('firstName')
                self.gov_business_poc_last_name = government_poc.get('lastName')

                _logger.info(f"SAM.gov data for {vendor_name} fetched and updated.")
            else:
                _logger.warning(f"No SAM.gov data found for {vendor_name}")
        else:
            _logger.error(f"Error fetching SAM.gov data: {response.status_code}")

    
    @api.depends('is_company')
    def _compute_vendor_number(self):
        for partner in self:
            if partner.is_company and isinstance(partner.id, int): # Check if vendor and `partner.id` is an integer
                partner.vendor_number = f'V{partner.id:06d}'
            else:
                partner.vendor_number = False