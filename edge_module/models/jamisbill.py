import requests
import json
import urllib3
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Optional

from odoo import models, fields, api

class JamisBills(models.Model):
    _name = 'jamis.bills'
    _description = 'Jamis Bills'

    move_id = fields.Many2one('account.move', string='Related Bill', required=True)
    jamis_id = fields.Char(string='Jamis ID', required=True)
    reference_number = fields.Char(string='Reference Number')
    creation_date = fields.Datetime(string='Creation Date', default=fields.Datetime.now)


@dataclass
class JamisBillDetail:
    id: Optional[str] = None
    Account: Optional[str] = None
    Amount: Optional[float] = None
    Branch: Optional[str] = None
    Description: Optional[str] = None
    ExtendedCost: Optional[float] = None
    InventoryID: Optional[str] = None
    NonBillable: Optional[bool] = None
    POLine: Optional[str] = None
    POOrderNbr: Optional[str] = None
    POOrderType: Optional[str] = None
    POReceiptLine: Optional[str] = None
    POReceiptNbr: Optional[str] = None
    Project: Optional[str] = None
    ProjectTask: Optional[str] = None
    Qty: Optional[float] = None
    Subaccount: Optional[str] = None
    TaxCategory: Optional[str] = None
    TransactionDescription: Optional[str] = None
    UnitCost: Optional[float] = None
    UOM: Optional[str] = None
    JobNumber: Optional[str] = None
    CostElement: Optional[str] = None
    Organization: Optional[str] = None

@dataclass
class JamisBill:
    id: Optional[str] = None
    ReferenceNbr: Optional[str] = None
    Vendor: Optional[str] = None
    VendorRef: Optional[str] = None
    Date: Optional[datetime] = None
    DueDate: Optional[datetime] = None
    Status: Optional[str] = None
    Amount: Optional[float] = None
    Balance: Optional[float] = None
    Description: Optional[str] = None
    Hold: Optional[bool] = None
    CurrencyID: Optional[str] = None
    Details: List[JamisBillDetail] = field(default_factory=list)

    def add_detail(self, detail: JamisBillDetail):
        self.Details.append(detail)
    def to_jamis_dict(self):
        """Convert the Bill object to a dictionary suitable for Acumatica API"""
        bill_dict = {
            "id": {"value": self.id},
            "ReferenceNbr": {"value": self.ReferenceNbr},
            "Vendor": {"value": self.Vendor},
            "VendorRef": {"value": self.VendorRef},
            "Date": {"value": self.Date.isoformat() if self.Date else None},
            "DueDate": {"value": self.DueDate.isoformat() if self.DueDate else None},
            "Status": {"value": self.Status},
            "Amount": {"value": self.Amount},
            "Balance": {"value": self.Balance},
            "Description": {"value": self.Description},
            "Hold": {"value": self.Hold},
            "CurrencyID": {"value": self.CurrencyID},
            "Details": []
        }
        
        for detail in self.Details:
            detail_dict = {attr: {"value": getattr(detail, attr)} for attr in JamisBillDetail.__annotations__}
            bill_dict["Details"].append(detail_dict)
        
        return bill_dict
    def from_jamis_dict(invoice_data: dict) -> 'JamisBill':
        """Create a Bill object from a dictionary returned by Acumatica API"""
        bill = JamisBill(
            id=invoice_data.get('id', {}),
            ReferenceNbr=invoice_data.get('ReferenceNbr', {}).get('value'),
            Vendor=invoice_data.get('Vendor', {}).get('value'),
            VendorRef = invoice_data.get('VendorRef', {}).get('value'),
            Date=datetime.fromisoformat(invoice_data.get('Date', {}).get('value')) if invoice_data.get('Date', {}).get('value') else None,
            DueDate=datetime.fromisoformat(invoice_data.get('DueDate', {}).get('value')) if invoice_data.get('DueDate', {}).get('value') else None,
            Status=invoice_data.get('Status', {}).get('value'),
            Amount=invoice_data.get('Amount', {}).get('value'),
            Balance=invoice_data.get('Balance', {}).get('value'),
            Description=invoice_data.get('Description', {}).get('value'),
            Hold=invoice_data.get('Hold', {}).get('value'),
            CurrencyID=invoice_data.get('CurrencyID', {}).get('value')
        )
        
        # Add details to the bill
        for detail_data in invoice_data.get('Details', []):
            detail = JamisBillDetail(
                id = detail_data.get('id', {}),
                Account=detail_data.get('Account', {}).get('value'),
                Amount=detail_data.get('Amount', {}).get('value'),
                Branch=detail_data.get('Branch', {}).get('value'),
                Description=detail_data.get('Description', {}).get('value'),
                ExtendedCost=detail_data.get('ExtendedCost', {}).get('value'),
                InventoryID=detail_data.get('InventoryID', {}).get('value'),
                NonBillable=detail_data.get('NonBillable', {}).get('value'),
                POLine=detail_data.get('POLine', {}).get('value'),
                POOrderNbr=detail_data.get('POOrderNbr', {}).get('value'),
                POOrderType=detail_data.get('POOrderType', {}).get('value'),
                POReceiptLine=detail_data.get('POReceiptLine', {}).get('value'),
                POReceiptNbr=detail_data.get('POReceiptNbr', {}).get('value'),
                Project=detail_data.get('Project', {}).get('value'),
                ProjectTask=detail_data.get('ProjectTask', {}).get('value'),
                Qty=detail_data.get('Qty', {}).get('value'),
                Subaccount=detail_data.get('Subaccount', {}).get('value'),
                TaxCategory=detail_data.get('TaxCategory', {}).get('value'),
                TransactionDescription=detail_data.get('TransactionDescription', {}).get('value'),
                UnitCost=detail_data.get('UnitCost', {}).get('value'),
                UOM=detail_data.get('UOM', {}).get('value'),
                JobNumber=detail_data.get('JobNumber', {}).get('value'),
                CostElement=detail_data.get('CostElement', {}).get('value'),
                Organization=detail_data.get('Organization', {}).get('value')
            )
            bill.add_detail(detail)
        
        return bill   
    def add_detail(self, detail: JamisBillDetail):
        self.Details.append(detail)
        self.Amount += detail.Amount
        self.Balance += detail.Amount
    def balance(self):
        total_amount = 0
        total_extended_amount = 0

        for detail in self.Details:
            
            amount = detail.Amount if detail.Amount is not None else 0
            extended_amount = detail.ExtendedCost if detail.ExtendedCost is not None else 0


            total_amount += amount
            total_extended_amount += extended_amount

        if abs(total_amount - total_extended_amount) < 0.01:  # Allow for small floating-point discrepancies
            self.Amount = total_amount
            self.Balance = total_amount
            return True
        else:
            raise ValueError(f"Total amount ({total_amount}) does not match total extended amount ({total_extended_amount})")
