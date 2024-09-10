import requests
import json
import urllib3
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Optional
from models.jamisbill import JamisBill
import logging

_logger = logging.getLogger(__name__)



# Disable SSL verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Replace these with your actual Acumatica/Jamis credentials and endpoint
BASE_URL = "https://ea.jamisprime.com/entity"
USERNAME = "JAMISAPIEA"
PASSWORD = "150w0esfd!"
COMPANY = "UAT08052024"  #Tenant
BRANCH = "AA"  #Company


def remove_none_values(d):
    if isinstance(d, dict):
        return {
            k: remove_none_values(v)
            for k, v in d.items()
            if not (isinstance(v, dict) and v.get('value') is None)
        }
    elif isinstance(d, list):
        return [remove_none_values(item) for item in d]
    else:
        return d

def get_bill_from_jamis(invoice_ref: str) -> JamisBill:
    # Authentication
    auth_data = {
        "name": USERNAME,
        "password": PASSWORD,
        "company": COMPANY
    }

    # Start a session
    session = requests.Session()
    session.verify = False  # Disable SSL verification
    auth_response = session.post(f"{BASE_URL}/auth/login", json=auth_data)
    auth_response.raise_for_status()

    invoice_endpoint = f"{BASE_URL}/EABill/20.200.001/Bill"

    params = {
        "$expand": "Details",
        "$filter": f"ReferenceNbr eq '{invoice_ref}'"
    }   

    try:
        response = session.get(invoice_endpoint, params=params)
        response.raise_for_status()
        invoices = response.json()
        print(invoices)
        
        if not invoices:
            print(f"No invoice found with reference number {invoice_ref}")
            return None
        
        invoice_data = invoices[0]
        
        
        bill = JamisBill.from_jamis_dict(invoice_data)
        _logger.info(f"Bill retrieved successfully: {bill}")
        _logger.info(f"Bill details: {bill.Details}")
        
        
        return bill

    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON response: {e}")
        print(f"Response content: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Invoice query failed: {e}")
        print(f"Response status code: {e.response.status_code if e.response else 'N/A'}")
        print(f"Response content: {e.response.text if e.response else 'N/A'}")
    finally:
        # Logout
        try:
            logout_response = session.post(f"{BASE_URL}/auth/logout")
            logout_response.raise_for_status()
            print("\nLogout successful")
        except requests.exceptions.RequestException as e:
            print(f"\nLogout failed: {e}")

    return None

def edit_bill_in_jamis(bill: JamisBill) -> Optional[str]:
    # Authentication
    auth_data = {
        "name": USERNAME,
        "password": PASSWORD,
        "company": COMPANY
    }

    # Start a session
    session = requests.Session()
    session.verify = False  # Disable SSL verification
    
    try:
        # Login
        auth_response = session.post(f"{BASE_URL}/auth/login", json=auth_data)
        auth_response.raise_for_status()
        
        
        # Prepare the bill data
        bill_data = bill.to_jamis_dict()
        bill_data = remove_none_values(bill_data)

        print(bill_data)
        

        # Not the change of endpoint.  I may try this without the ReferenceNbr in the payload
        bill_endpoint = f"{BASE_URL}/EABill/20.200.001/Bill"

        # Edit the bill.  I think we need to go by id here.   We should pull the OG bill and then edit it.
        params = {
            "$expand": "Details",
            "$filter": f"id eq '{bill.id}'"
        } 
        
        
        response = session.put(bill_endpoint, params=params, json=bill_data)
        response.raise_for_status()

        # Parse the response to get the new bill number
        bill_data = response.json()
        return bill_data 

    except requests.exceptions.RequestException as e:
        print(f"Failed to create bill: {e}")
        if hasattr(e, 'response'):
            print(f"Response status code: {e.response.status_code}")
            print(f"Response content: {e.response.text}")
        return None
    finally:
        # Logout
        try:
            logout_response = session.post(f"{BASE_URL}/auth/logout")
            logout_response.raise_for_status()
            print("Logout successful")
        except requests.exceptions.RequestException as e:
            print(f"Logout failed: {e}")

def create_bill_in_jamis(bill: JamisBill) -> Optional[str]:
    # Authentication
    auth_data = {
        "name": USERNAME,
        "password": PASSWORD,
        "company": COMPANY
    }

    # Start a session
    session = requests.Session()
    session.verify = False  # Disable SSL verification
    
    try:
        # Login
        auth_response = session.post(f"{BASE_URL}/auth/login", json=auth_data)
        auth_response.raise_for_status()
        
        
        # Prepare the bill data
        bill_data = bill.to_jamis_dict()
        bill_data = remove_none_values(bill_data)

        print(bill_data)
        

        # Not the change of endpoint.  I may try this without the ReferenceNbr in the payload
        bill_endpoint = f"{BASE_URL}/EABill/20.200.001/Bill"

        # Edit the bill.  I think we need to go by id here.   We should pull the OG bill and then edit it.
        params = {
            "$expand": "Details",
        } 
        
        
        response = session.put(bill_endpoint, params=params, json=bill_data)
        response.raise_for_status()

        # Parse the response to get the new bill number
        bill_data = response.json()
        return bill_data 

    except requests.exceptions.RequestException as e:
        print(f"Failed to create bill: {e}")
        if hasattr(e, 'response'):
            print(f"Response status code: {e.response.status_code}")
            print(f"Response content: {e.response.text}")
        return None
    finally:
        # Logout
        try:
            logout_response = session.post(f"{BASE_URL}/auth/logout")
            logout_response.raise_for_status()
            print("Logout successful")
        except requests.exceptions.RequestException as e:
            print(f"Logout failed: {e}")
