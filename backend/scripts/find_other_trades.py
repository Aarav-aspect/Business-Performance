"""
find_other_trades.py
Run from backend/ directory:  python find_other_trades.py

Queries Salesforce directly and writes other_trades_report.txt listing
every Job_Trade__c value that falls into "Other".
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from salesforce_client import sf_client, TRADE_REVERSE_MAP
from collections import defaultdict

sf = sf_client.sf  # the underlying simple_salesforce.Salesforce object

print("Fetching invoices...")
inv_res = sf.query_all("""
    SELECT Job_Trade__c
    FROM Customer_Invoice__c
    WHERE (Date__c = LAST_N_MONTHS:13 OR Date__c = THIS_MONTH)
    AND Chumley_Test_Record__c = False
""")

print("Fetching payments...")
pay_res = sf.query_all("""
    SELECT Customer_Invoice__r.Job_Trade__c
    FROM asp04__Payment__c
    WHERE (asp04__Payment_Date__c = LAST_N_MONTHS:13 OR asp04__Payment_Date__c = THIS_MONTH)
""")

# Collect: trade_name -> {invoices, payments}
data = defaultdict(lambda: {"invoices": 0, "payments": 0})

for r in inv_res.get("records", []):
    name = r.get("Job_Trade__c") or "(empty/null)"
    if name not in TRADE_REVERSE_MAP:
        data[name]["invoices"] += 1

for r in pay_res.get("records", []):
    inv_rel = r.get("Customer_Invoice__r") or {}
    name = inv_rel.get("Job_Trade__c") or "(empty/null)"
    if name not in TRADE_REVERSE_MAP:
        data[name]["payments"] += 1

# Write report
out_path = os.path.join(os.path.dirname(__file__), "other_trades_report.txt")
with open(out_path, "w") as f:
    if not data:
        f.write("No unrecognised trade names found — nothing is going into Other.\n")
    else:
        header = f"{'Trade Name':<60} {'Invoices':>9} {'Payments':>9}\n"
        f.write(header)
        f.write("-" * 80 + "\n")
        for name, counts in sorted(data.items(), key=lambda x: -(x[1]["invoices"] + x[1]["payments"])):
            f.write(f"{name:<60} {counts['invoices']:>9} {counts['payments']:>9}\n")

print(f"Report written to: {out_path}")
