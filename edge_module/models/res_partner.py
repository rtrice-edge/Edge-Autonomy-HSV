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
    physical_address_line1 = fields.Char(string="Physical Address Line 1")
    physical_address_line2 = fields.Char(string="Address Line 2")
    physical_city = fields.Char(string="Physical City")
    physical_state_or_province = fields.Char(string="Physical State/Province")
    physical_zip_code = fields.Char(string="Physical ZIP Code")
    physical_zip_plus4 = fields.Char(string="Physical ZIP Code Plus 4")
    physical_country_code = fields.Char(string="Physical Country Code")

    # Business type list fields (storing as text; you can modify based on your need)
    business_type_list = fields.Text(string="Business Types")

    credit_card_usage = fields.Char(string="Credit Card Usage")
    debt_subject_to_offset = fields.Char(string="Debt Subject to Offset")
    psc_description = fields.Text(string="PSC Description")
    
    # Points of contact
    gov_business_poc_first_name = fields.Char(string="Government Business POC First Name")
    gov_business_poc_last_name = fields.Char(string="Government Business POC Last Name")

    # exclusion_status_flag = fields.Char(string="Exclusion Status Flag", store=True, readonly=False)
    # exclusion_status_name = fields.Char(string="Exclusion Status", compute="_compute_exclusion_status_name")
    # exclusion_status_description = fields.Text(string="", compute="_compute_exclusion_status_description")

    @api.model
    def fetch_sam_data(self):
        base_url = "https://api.sam.gov/entity-information/v2/entities"
        if self.sam_uei:
            params = {
                "api_key": 'p8PR2hlkd1icfx0LlidcVfygSQpxrDfBUgVV1OsV',
                "ueiSAM": self.sam_uei,
            }
        else:
            # Fall back to the original search parameters
            params = {
                "api_key": 'p8PR2hlkd1icfx0LlidcVfygSQpxrDfBUgVV1OsV',
                "legalBusinessName": self.name,
                "physicalAddressCity": self.city,
            }

        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()  # Raises an HTTPError for bad responses
            
            data = response.json()
            if data['totalRecords'] > 0:
                entity_data = data['entityData'][0]
                registration = entity_data['entityRegistration']
                core_data = entity_data['coreData']
                physical_address = core_data.get('physicalAddress', {})
                business_types = core_data.get('businessTypes', {}).get('businessTypeList', [])
                government_poc = entity_data.get('pointsOfContact', {}).get('governmentBusinessPOC', {})

                # Update fields based on API response
                self.sam_uei = registration.get('ueiSAM')
                self.legal_business_name = registration.get('legalBusinessName')
                self.uei_status = registration.get('ueiStatus')
                self.uei_creation_date = registration.get('ueiCreationDate')
                self.entity_url = core_data.get('entityInformation', {}).get('entityURL')
                self.entity_start_date = core_data.get('entityInformation', {}).get('entityStartDate')
                self.entity_structure_desc = core_data.get('generalInformation', {}).get('entityStructureDesc')
                # self.exclusion_status_flag = registration.get('exclusionStatusFlag')

                # Physical address fields
                self.physical_address_line1 = physical_address.get('addressLine1')
                self.physical_address_line2 = physical_address.get('addressLine2')
                self.physical_city = physical_address.get('city')
                self.physical_state_or_province = physical_address.get('stateOrProvinceCode')
                self.physical_zip_code = physical_address.get('zipCode')
                self.physical_zip_plus4 = physical_address.get('zipCodePlus4')
                self.physical_country_code = physical_address.get('countryCode')

                # Business types
                self.business_type_list = ', '.join(filter(None, [bt.get('businessTypeDesc') for bt in business_types]))

                # Financial Information
                financial_info = core_data.get('financialInformation', {})
                self.credit_card_usage = financial_info.get('creditCardUsage')
                self.debt_subject_to_offset = financial_info.get('debtSubjectToOffset')

                # PSC description
                psc_list = entity_data.get('assertions', {}).get('goodsAndServices', {}).get('pscList', [])
                self.psc_description = ', '.join(filter(None, [psc.get('pscDescription') for psc in psc_list]))

                # Government Business POC
                self.gov_business_poc_first_name = government_poc.get('firstName')
                self.gov_business_poc_last_name = government_poc.get('lastName')

                _logger.info(f"SAM.gov data for {self.name} fetched and updated.")
            else:
                _logger.warning(f"No SAM.gov data found for {self.name}")
        except requests.RequestException as e:
            _logger.error(f"Error fetching SAM.gov data: {str(e)}")
        except KeyError as e:
            _logger.error(f"Unexpected data structure in SAM.gov response: {str(e)}")
        except Exception as e:
            _logger.error(f"Unexpected error while processing SAM.gov data: {str(e)}")


    def action_fetch_sam_data(self):
        self.ensure_one()
        self.fetch_sam_data()
        return True
    
    @api.depends('is_company')
    def _compute_vendor_number(self):
        for partner in self:
            if partner.is_company and isinstance(partner.id, int): # Check if vendor and `partner.id` is an integer
                partner.vendor_number = f'V{partner.id:06d}'
            else:
                partner.vendor_number = False

    # @api.depends('exclusion_status_flag')
    # def _compute_exclusion_status_name(self):
    #     for record in self:
    #         exclusion_status_map = {
    #             'P': 'Ineligible (Proceedings Completed)',
    #             'J1': 'Ineligible (Proceedings Pending)',
    #             'RR': 'Ineligible (Proceedings Completed)',
    #             'A1': 'Ineligible (Proceedings Pending)',
    #             'B': 'Ineligible (Proceedings Pending)',
    #             'M': 'Prohibition/Restriction',
    #             'Z1': 'Prohibition/Restriction',
    #             'G': 'Ineligible (Proceedings Completed)',
    #             'SS': 'Ineligible (Proceedings Completed)',
    #             'QQ': 'Prohibition/Restriction',
    #             'A': 'Ineligible (Proceedings Completed)',
    #             'L': 'Ineligible (Proceedings Completed)',
    #             'Q': 'Ineligible (Proceedings Pending)',
    #             'F': 'Ineligible (Proceedings Completed)',
    #             'I': 'Ineligible (Proceedings Completed)',
    #             'VV': 'Prohibition/Restriction',
    #             'D': 'Ineligible (Proceedings Completed)',
    #             'N1': 'Ineligible (Proceedings Pending)',
    #             'R': 'Ineligible (Proceedings Completed)',
    #             'S': 'Ineligible (Proceedings Pending)',
    #             'T': 'Voluntary Exclusion',
    #             'V': 'Ineligible (Proceedings Completed)',
    #             'W': 'Ineligible (Proceedings Pending)',
    #             'X': 'Prohibition/Restriction',
    #             'K': 'Ineligible (Proceedings Pending)',
    #             'N': 'Ineligible (Proceedings Completed)',
    #             'O': 'Ineligible (Proceedings Pending)',
    #             'AA': 'Ineligible (Proceedings Completed)',
    #             'BB': 'Prohibition/Restriction',
    #             'DD': 'Ineligible (Proceedings Completed)',
    #             'EE': 'Ineligible (Proceedings Completed)',
    #             '03-SDNT-01': 'Prohibition/Restriction',
    #             'C': 'Ineligible (Proceedings Completed)',
    #             'C1': 'Ineligible (Proceedings Completed)',
    #             'E': 'Ineligible (Proceedings Completed)',
    #             'H': 'Prohibition/Restriction',
    #             '03-SDNTK-01': 'Prohibition/Restriction',
    #             'Z3': 'Prohibition/Restriction',
    #             'GG': 'Ineligible (Proceedings Completed)',
    #             'XXX': 'Prohibition/Restriction',
    #             'YYY': 'Prohibition/Restriction',
    #             'ZZZ': 'Prohibition/Restriction',
    #             'Z2': 'Prohibition/Restriction',
    #             'RRR': 'Ineligible (Proceedings Completed)',
    #             'VVV': 'Prohibition/Restriction',
    #             'JJ': 'Prohibition/Restriction',
    #             'H2': 'Prohibition/Restriction',
    #             'JJJ': 'Prohibition/Restriction',
    #             'R1': 'Ineligible (Proceedings Completed)',
    #             'S1': 'Ineligible (Proceedings Pending)',
    #             '03-SDT-01': 'Prohibition/Restriction',
    #             '03-BSE-01': 'Prohibition/Restriction',
    #             '03-DP-01': 'Prohibition/Restriction',
    #             '10-VA-01': 'Ineligible (Proceedings Completed)',
    #             'I1': 'Ineligible (Proceedings Completed)',
    #             '10-VA-02': 'Ineligible (Proceedings Completed)',
    #             '10-ISA-01': 'Prohibition/Restriction',
    #             'BPI-SDNTK': 'Prohibition/Restriction',
    #             'J': 'Ineligible (Proceedings Completed)',
    #             'CC': 'Ineligible (Proceedings Completed)',
    #             'U': 'Ineligible (Proceedings Completed)',
    #             '03-ENT-01': 'Prohibition/Restriction',
    #             '03-FTO-01': 'Prohibition/Restriction',
    #             '03-SDGT-01': 'Prohibition/Restriction',
    #             '03-SDN-01': 'Prohibition/Restriction',
    #             '03-TLGE-01': 'Prohibition/Restriction',
    #             'BPI-SDGT': 'Prohibition/Restriction',
    #             'BPI-SDNT': 'Prohibition/Restriction',
    #             '08-INA-01': 'Ineligible (Proceedings Completed)',
    #             '10-CIS-01': 'Prohibition/Restriction',
    #             '08-INA-02': 'Ineligible (Proceedings Completed)',
    #             '11-USDA-01': 'Prohibition/Restriction',
    #             'Z': 'Prohibition/Restriction'
    #         }
    #         record.exclusion_status_name = exclusion_status_map.get(record.exclusion_status_flag, False)

    # @api.depends('exclusion_status_name')
    # def _compute_exclusion_status_description(self):
    #     for record in self:
    #         description = False
    #         if record.exclusion_status_name == 'Prohibition/Restriction':
    #             description = """Nature (Cause): May be subject to sanctions pursuant to the conditions imposed by the U.S. Department of the Treasury Office of Foreign Assets Control (OFAC), or subject to sanction, restriction or partial denial pursuant to the conditions imposed by the U.S. Department of State or Federal agency of the U.S. Government.

    # Effect: If you think you have a potential match with an OFAC listing, please visit the Treasury Department website for guidance. For all other prohibitions and restrictions, see the agency note in the Additional Comments field to ascertain the extent or limit on the sanction, restriction or partial denial. If there is no note, contact the agency taking the action for this information."""
            
    #         elif record.exclusion_status_name == 'Ineligible (Proceedings Pending)':
    #             description = """Nature (Cause): Preliminarily ineligible based upon adequate evidence of conduct indicating a lack of business honesty or integrity, or a lack of business integrity, or regulation, statute, executive order or other legal authority, pending completion of an investigation and/or legal proceedings; or based upon initiation of proceedings to determine final ineligibility based upon regulation, statute, executive order or other legal authority or a lack of business integrity or a preponderance of evidence of any other cause of a serious and compelling nature that it affects present responsibility.

    # Effect: Procurement - Agencies shall not solicit offers from, award contracts to renew, place new orders with, or otherwise extend the duration of current contracts, or consent to subcontracts in excess of $30,000 (other than commercially available off-the-shelf items), with these contractors unless the agency head determines in writing there is a compelling reason to do so.

    # Nonprocurement - No agency in the Executive Branch shall enter into, renew, or extend primary or lower tier covered transactions to a participant or principal determined preliminarily ineligible unless the head of the awarding agency grants a compelling reasons exception in writing."""
            
    #         elif record.exclusion_status_name == 'Voluntary Exclusion':
    #             description = """Nature (Cause): Accepted an agreement to be excluded under the terms of a settlement between the person and one or more agencies.

    # Effect: These persons are excluded in accordance with the terms of their voluntary exclusion agreement. See the agency note in the Additional Comments field to ascertain the extent of the exclusion or the limit on the person's participation, in covered transactions. If there is no note, contact the agency taking the action for this information."""
            
    #         elif record.exclusion_status_name == 'Ineligible (Proceedings Completed)':
    #             description = """Nature (Cause): Determined ineligible upon completion of administrative proceedings establishing by preponderance of the evidence of a cause of a serious and compelling nature that it affects present responsibility, or determined ineligible based on other regulation, statute, executive order or other legal authority.

    # Effect: Procurement - Agencies shall not solicit offers from, award contracts to renew, place new orders with, or otherwise extend the duration of current contracts, or consent to subcontracts in excess of $30,000 (other than commercially available off-the-shelf items), with these contractors unless the agency head determines in writing there is a compelling reason to do so.

    # Nonprocurement - No agency in the Executive Branch shall enter into, renew, or extend primary or lower tier covered transactions to a participant or principal determined ineligible unless the head of the awarding agency grants a compelling reasons exception in writing."""
            
    #         record.exclusion_status_description = description