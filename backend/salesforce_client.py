"""
salesforce_client.py — Salesforce connection + shared constants.

All SOQL compute methods have been migrated to data_processor.py (Pandas).
Raw data fetching now lives in world_view.py (WorldViewCache).
This module exists solely for the SF connection singleton and trade mapping constants.
"""

import os
import threading
from typing import Dict, List, Tuple
from simple_salesforce import Salesforce
from dotenv import load_dotenv
from homeowner_mapping import postcode_to_region  # noqa: F401 — re-exported for convenience

load_dotenv()

HOMEOWNER_SECTOR = 'Home Owner'

TRADE_SUBGROUPS = {
    "HVac & Electrical": {
        "Air Conditioning": ["Air Con, Ventilation & Refrigeration"],
        "Gas & Heating": ["Heating & Hot Water (Domestic)", "Heating & Hot Water (Commercial)", "Gas", "HVAC", "Heating Renewable"],
        "Electrical": ["Electrical", "Electrical Renewable"],
    },
    "Building Fabric": {
        "Decoration": ["Decorating", "Plastering", "Tiling", "Wallpapering", "Multi", "Decoration"],
        "Roofing": ["Roofing/LeakDetection", "Roofing", "Roof Window & Gutter Cleaning", "Roofing/Leak Detection"],
        "Multi Trades": ["Windows & Doors", "Handyman", "Carpentry", "Flooring Trade", "Fencing",
                         "Brickwork & Paving", "Locksmithing", "Partition Walls & Ceilings", "Access", "Glazing"],
        "Project Management": ["Project Management Refurbishment", "General Refurbishment",
                               "Bathroom Refurbishment", "Project Management Decoration"],
    },
    "Environmental Services": {
        "Gardening": ["Gardening"],
        "Pest Control": ["Pest Control", "Pest Proofing"],
        "Specialist Cleaning": ["Sanitisation & specialist cleaning"],
        "Waste and Grease Management": ["Rubbish Removal"],
    },
    "Fire Safety": {
        "Fire Safety": ["Fire Safety", "Fire Safety Consultation", "Vent Hygiene and Safety"],
    },
    "Leak, Damp & Restoration": {
        "Leak Detection": [
            "Leak Detection", "Leak Detection Restoration", "Leak Detection Restoration Drainage",
            "Leak Detection Restoration Plumbing", "Leak Detection Restoration Central Heating",
            "LD Commercial Mains Water Leak", "LD commercial Gas", "LD Damp Restoration",
            "Leak Detection Building Fabric", "Leak Detection Domestic Plumbing",
            "Leak Detection Industrial Plumbing", "Leak Detection Domestic Gas & Heating",
            "Leak Detection Commercial Gas & Heating", "Leak Detection Industrial Gas & Heating",
            "Leak Detection Diving",
            "Leak Detection Restoration Domestic Plumbing", "Leak Detection Commercial Plumbing",
            "Leak Detection Restoration Domestic Central Heating", "Leak Detection Restoration Commercial Plumbing",
            "Leak Detection Restoration Domestic Drainage", "Leak Detection HVAC", "Leak Monitoring"
        ],
        "Damp": ["Damp & Mould", "Damp Proofing", "Damp Survey", "Mould Survey",
                 "Damp Survey Roofing", "Damp"],
        "Restoration": ["Drying", "LDR, Restoration", "Structural Drying & Certification"]
    },
    "Plumbing & Drainage": {
        "Plumbing": ["Plumbing", "Plumbing & Cold Water"],
        "Drainage": ["Drainage (Soil Water)", "Drainage (Wastewater)", "Drainage Restoration",
                     "Drainage (Tanker)", "Commercial Pumps", "Drainage (Septic Tanks)",
                     "Drainage", "Drainage Leak Detection"],
    },
    "Utilities": {
        "Utilities": ["Utilities", "Utilities - Blended - General Building", "Utilities - Blended - Drainage"]
    }
}

TRADE_REVERSE_MAP: Dict[str, Tuple[str, str]] = {}
for _macro, _subs in TRADE_SUBGROUPS.items():
    for _sub_name, _trades in _subs.items():
        for _t in _trades:
            TRADE_REVERSE_MAP[_t] = (_macro, _sub_name)


def _build_sector_clause(sectors=None, via_invoice_rel=False) -> str:
    """Build SOQL WHERE clause fragment for sector filtering (used by debug endpoint)."""
    if not sectors:
        return ""
    field = "Customer_Invoice__r.Sector_Type__c" if via_invoice_rel else "Sector_Type__c"
    quoted = ", ".join(f"'{s}'" for s in sectors)
    return f"AND {field} IN ({quoted})"


class SalesforceClient:
    def __init__(self):
        self.sf = Salesforce(
            username=os.getenv("SF_USERNAME"),
            password=os.getenv("SF_PASSWORD"),
            security_token=os.getenv("SF_SECURITY_TOKEN"),
            domain=os.getenv("SF_DOMAIN", "login")
        )

    def get_distinct_sectors(self) -> List[str]:
        """Fallback: fetch distinct sectors directly from Salesforce (used if world view unavailable)."""
        query = """
            SELECT Sector_Type__c
            FROM Customer_Invoice__c
            WHERE Sector_Type__c != NULL AND Chumley_Test_Record__c = False
        """
        try:
            res = self.sf.query_all(query)
            return sorted(set(
                r['Sector_Type__c'] for r in res.get('records', []) if r.get('Sector_Type__c')
            ))
        except Exception as e:
            print(f"Distinct Sectors Error: {e}")
            return []


sf_client = SalesforceClient()
