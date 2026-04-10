import os
from typing import Any, Dict, List, Optional
from simple_salesforce import Salesforce
from dotenv import load_dotenv

load_dotenv()

def check_salesforce_connection() -> bool:
    """Simple check to verify Salesforce connection and imports."""
    try:
        sf = Salesforce(
            username=os.getenv("SF_USERNAME"),
            password=os.getenv("SF_PASSWORD"),
            security_token=os.getenv("SF_SECURITY_TOKEN"),
            domain=os.getenv("SF_DOMAIN", "login")
        )
        print("Successfully connected to Salesforce")
        return True
    except Exception as e:
        print(f"Salesforce connection failed: {e}")
        return False

if __name__ == "__main__":
    check_salesforce_connection()
