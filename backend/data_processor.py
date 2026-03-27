"""
data_processor.py — Filter and compute all dashboard metrics from WorldViewCache DataFrames.

No Salesforce I/O here. All functions accept a dict of Pandas DataFrames returned by
WorldViewCache.get_world_view(), apply optional filters, and compute metrics.
"""

import math
import calendar
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

HOMEOWNER_SECTOR = 'Home Owner'

# Imported from salesforce_client constants
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


def _r(val: Any, ndigits: int = 2) -> float:
    try:
        return round(float(val), ndigits)
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------

def filter_dataframes(
    wv: Dict[str, pd.DataFrame],
    sectors: Optional[Tuple] = None,
    account_type: Optional[Tuple] = None,
    homeowner_region: Optional[Tuple] = None,
) -> Dict[str, pd.DataFrame]:
    """
    Apply sector / account_type / homeowner_region filters to all DataFrames.
    When homeowner_region is set, sectors is forced to ('Home Owner',).
    Returns a new dict of filtered DataFrames (originals are not mutated).
    """
    if homeowner_region:
        sectors = (HOMEOWNER_SECTOR,)

    invoices = wv.get('invoices', pd.DataFrame()).copy()
    credits = wv.get('credits', pd.DataFrame()).copy()
    payments = wv.get('payments', pd.DataFrame()).copy()
    sas = wv.get('sas', pd.DataFrame()).copy()
    outstanding = wv.get('outstanding', pd.DataFrame()).copy()

    # --- Invoices ---
    if sectors and not invoices.empty and 'Sector_Type__c' in invoices.columns:
        invoices = invoices[invoices['Sector_Type__c'].isin(sectors)]
    if account_type and not invoices.empty and 'account_type' in invoices.columns:
        invoices = invoices[invoices['account_type'].isin(account_type)]
    if homeowner_region and not invoices.empty and 'region' in invoices.columns:
        invoices = invoices[invoices['region'].isin(homeowner_region)]

    # --- Credits (filter by invoice_sector and invoice_account_type) ---
    if sectors and not credits.empty and 'invoice_sector' in credits.columns:
        credits = credits[credits['invoice_sector'].isin(sectors)]
    if account_type and not credits.empty and 'invoice_account_type' in credits.columns:
        credits = credits[credits['invoice_account_type'].isin(account_type)]
    if homeowner_region and not credits.empty and 'region' in credits.columns:
        credits = credits[credits['region'].isin(homeowner_region)]

    # --- Payments (filter by invoice_sector and invoice_account_type) ---
    if sectors and not payments.empty and 'invoice_sector' in payments.columns:
        payments = payments[payments['invoice_sector'].isin(sectors)]
    if account_type and not payments.empty and 'invoice_account_type' in payments.columns:
        payments = payments[payments['invoice_account_type'].isin(account_type)]
    if homeowner_region and not payments.empty and 'region' in payments.columns:
        payments = payments[payments['region'].isin(homeowner_region)]

    # --- Service Appointments ---
    # SAs don't have a Sector_Type__c — sector filter via region only for homeowner
    if homeowner_region and not sas.empty and 'region' in sas.columns:
        sas = sas[sas['region'].isin(homeowner_region)]
    if account_type and not sas.empty and 'account_type' in sas.columns:
        sas = sas[sas['account_type'].isin(account_type)]

    # --- Outstanding ---
    if sectors and not outstanding.empty and 'Sector_Type__c' in outstanding.columns:
        outstanding = outstanding[outstanding['Sector_Type__c'].isin(sectors)]
    if account_type and not outstanding.empty and 'account_type' in outstanding.columns:
        outstanding = outstanding[outstanding['account_type'].isin(account_type)]
    if homeowner_region and not outstanding.empty and 'region' in outstanding.columns:
        outstanding = outstanding[outstanding['region'].isin(homeowner_region)]

    return {
        'invoices': invoices.reset_index(drop=True),
        'credits': credits.reset_index(drop=True),
        'payments': payments.reset_index(drop=True),
        'sas': sas.reset_index(drop=True),
        'outstanding': outstanding.reset_index(drop=True),
    }


# ---------------------------------------------------------------------------
# Compute functions
# ---------------------------------------------------------------------------

def compute_sectors(filtered_dfs: Dict[str, pd.DataFrame]) -> List[str]:
    """Return sorted list of distinct Sector_Type__c values from invoices."""
    inv = filtered_dfs.get('invoices', pd.DataFrame())
    if inv.empty or 'Sector_Type__c' not in inv.columns:
        return []
    return sorted(inv['Sector_Type__c'].dropna().unique().tolist())


def compute_summary_metrics(
    filtered_dfs: Dict[str, pd.DataFrame],
    today: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Equivalent to SalesforceClient.get_summary_metrics().
    Returns: {invoices: {cnt, total_sales}, credits: {total_credits, credits_this_month_invoice,
              credits_prev_invoice}, collections: {total_collected}}
    """
    if today is None:
        today = date.today()
    cy, cm = today.year, today.month

    inv = filtered_dfs.get('invoices', pd.DataFrame())
    cred = filtered_dfs.get('credits', pd.DataFrame())
    pay = filtered_dfs.get('payments', pd.DataFrame())

    # --- Invoices this month ---
    inv_mtd = inv[(inv['year'] == cy) & (inv['month'] == cm)] if not inv.empty else pd.DataFrame()
    inv_cnt = len(inv_mtd)
    inv_total_sales = float(inv_mtd['Charge_Net__c'].sum()) if not inv_mtd.empty else 0.0

    # --- Credits this month (credit Date__c = this month) ---
    cred_mtd = cred[(cred['year'] == cy) & (cred['month'] == cm)] if not cred.empty else pd.DataFrame()
    total_credits = float(cred_mtd['Charge_Net__c'].sum()) if not cred_mtd.empty else 0.0

    # --- Credits on this month's invoices (invoice_date = this month) ---
    if not cred.empty and 'invoice_date' in cred.columns:
        inv_date_dt = pd.to_datetime(cred['invoice_date'].str[:10], errors='coerce')
        cred_this_inv = cred[
            (inv_date_dt.dt.year == cy) & (inv_date_dt.dt.month == cm)
        ]
        credits_this_month_invoice = float(cred_this_inv['Charge_Net__c'].sum())
    else:
        credits_this_month_invoice = 0.0
    credits_prev_invoice = max(0.0, total_credits - credits_this_month_invoice)

    # --- MTD Collections ---
    # Payments: stage=Collected, invoice_date=this month, payment_date=this month
    collected_net = 0.0
    if not pay.empty:
        pay_mtd = pay[
            (pay.get('asp04__Payment_Stage__c', pd.Series()) == 'Collected from customer') if 'asp04__Payment_Stage__c' in pay.columns else pd.Series(True, index=pay.index)
        ]
        if 'asp04__Payment_Stage__c' in pay.columns:
            pay_mtd = pay[pay['asp04__Payment_Stage__c'] == 'Collected from customer']
        else:
            pay_mtd = pay.copy()

        # Filter to invoice_date=this month
        if 'invoice_date' in pay_mtd.columns:
            inv_dt = pd.to_datetime(pay_mtd['invoice_date'].str[:10], errors='coerce')
            pay_mtd = pay_mtd[(inv_dt.dt.year == cy) & (inv_dt.dt.month == cm)]

        # Filter to payment_date=this month
        pay_mtd = pay_mtd[(pay_mtd['year'] == cy) & (pay_mtd['month'] == cm)]

        if not pay_mtd.empty:
            # Build credit map: invoice_name → total credits (from MTD credits)
            cred_for_match = cred_mtd if not cred_mtd.empty else pd.DataFrame()
            if not cred_for_match.empty and 'invoice_name' in cred_for_match.columns:
                credit_map = cred_for_match.groupby('invoice_name')['Charge_Net__c'].sum()
            else:
                credit_map = pd.Series(dtype=float)

            for _, row in pay_mtd.iterrows():
                amt = float(row.get('asp04__Amount__c', 0) or 0)
                inv_name = row.get('invoice_name')
                credit_amt = float(credit_map.get(inv_name, 0.0)) if inv_name and len(credit_map) else 0.0
                collected_net += (amt / 1.2) - credit_amt

    return {
        "invoices": {"cnt": inv_cnt, "total_sales": inv_total_sales},
        "credits": {
            "total_credits": total_credits,
            "credits_this_month_invoice": credits_this_month_invoice,
            "credits_prev_invoice": credits_prev_invoice,
        },
        "collections": {"total_collected": collected_net},
    }


def compute_sales_trend(
    filtered_dfs: Dict[str, pd.DataFrame],
    today: Optional[date] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Equivalent to SalesforceClient.get_sales_trend().
    Returns: {invoices: [{year, month, total}], credits: [{year, month, total}], today_net: float}
    """
    if today is None:
        today = date.today()
    inv = filtered_dfs.get('invoices', pd.DataFrame())
    cred = filtered_dfs.get('credits', pd.DataFrame())

    def _monthly(df: pd.DataFrame) -> List[Dict]:
        if df.empty or 'year' not in df.columns:
            return []
        grp = df.groupby(['year', 'month'])['Charge_Net__c'].sum().reset_index()
        return [{'year': int(r['year']), 'month': int(r['month']), 'total': float(r['Charge_Net__c'])}
                for _, r in grp.iterrows()]

    today_str = today.isoformat()
    today_inv = 0.0
    today_cred = 0.0
    if not inv.empty and 'Date__c' in inv.columns:
        inv_today = inv[inv['Date__c'].astype(str).str[:10] == today_str]
        today_inv = float(inv_today['Charge_Net__c'].sum()) if not inv_today.empty else 0.0
    if not cred.empty and 'Date__c' in cred.columns:
        cred_today = cred[cred['Date__c'].astype(str).str[:10] == today_str]
        today_cred = float(cred_today['Charge_Net__c'].sum()) if not cred_today.empty else 0.0

    return {'invoices': _monthly(inv), 'credits': _monthly(cred), 'today_net': round(today_inv - today_cred, 2)}


def compute_collections_data(
    filtered_dfs: Dict[str, pd.DataFrame],
    today: Optional[date] = None,
) -> Dict[str, Any]:
    """Equivalent to SalesforceClient.get_collections_data()."""
    if today is None:
        today = date.today()
    cy, cm = today.year, today.month
    months_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    pay = filtered_dfs.get('payments', pd.DataFrame())
    cred = filtered_dfs.get('credits', pd.DataFrame())

    if pay.empty:
        return {"total": 0.0, "target": _r(3500000.0 / 1.2), "by_sector": [], "history": []}

    collected_pay = pay[pay.get('asp04__Payment_Stage__c', pd.Series()) == 'Collected from customer'] if 'asp04__Payment_Stage__c' in pay.columns else pay.copy()

    # -- MTD: invoice_date=this month, payment_date=this month --
    mtd_pay = collected_pay.copy()
    if 'invoice_date' in mtd_pay.columns:
        inv_dt = pd.to_datetime(mtd_pay['invoice_date'].str[:10], errors='coerce')
        mtd_pay = mtd_pay[(inv_dt.dt.year == cy) & (inv_dt.dt.month == cm)]
    mtd_pay = mtd_pay[(mtd_pay['year'] == cy) & (mtd_pay['month'] == cm)]

    # MTD credit map (credit Date__c = this month)
    cred_mtd = cred[(cred['year'] == cy) & (cred['month'] == cm)] if not cred.empty else pd.DataFrame()
    mtd_credit_map: Dict[str, float] = {}
    if not cred_mtd.empty and 'invoice_name' in cred_mtd.columns:
        mtd_credit_map = cred_mtd.groupby('invoice_name')['Charge_Net__c'].sum().to_dict()

    by_sector: Dict[str, float] = {}
    by_trade_group: Dict[str, float] = {}
    total_mtd = 0.0
    for _, row in mtd_pay.iterrows():
        amt = float(row.get('asp04__Amount__c', 0) or 0)
        inv_name = row.get('invoice_name')
        sector = row.get('invoice_sector') or 'Unknown'
        credit = mtd_credit_map.get(inv_name, 0.0) if inv_name else 0.0
        net = (amt / 1.2) - credit
        total_mtd += net
        by_sector[sector] = by_sector.get(sector, 0.0) + net
        raw_trade = row.get('invoice_trade_group') or ''
        macro_group, _ = TRADE_REVERSE_MAP.get(raw_trade, ('Other', 'Other'))
        by_trade_group[macro_group] = by_trade_group.get(macro_group, 0.0) + net

    # -- Historical trend: group payments by (year, month), credit match by (year, month, inv_name) --
    hist_credit_map: Dict[Tuple, float] = {}
    if not cred.empty and 'invoice_name' in cred.columns:
        for _, row in cred.iterrows():
            inv = row.get('invoice_name')
            y, m = row.get('year'), row.get('month')
            if inv and y and m:
                key = (int(y), int(m), inv)
                hist_credit_map[key] = hist_credit_map.get(key, 0.0) + float(row.get('Charge_Net__c', 0) or 0)

    hist_buckets: Dict[Tuple, float] = {}
    for _, row in collected_pay.iterrows():
        y, m = row.get('year'), row.get('month')
        inv = row.get('invoice_name')
        amt = float(row.get('asp04__Amount__c', 0) or 0)
        if y and m:
            match_key = (int(y), int(m), inv) if inv else None
            credit_val = hist_credit_map.get(match_key, 0.0) if match_key else 0.0
            bucket = (int(y), int(m))
            hist_buckets[bucket] = hist_buckets.get(bucket, 0.0) + (amt / 1.2) - credit_val

    history = []
    for (y, m), total in hist_buckets.items():
        history.append({
            "month": f"{months_names[m - 1]} {str(y)[-2:]}",
            "value": _r(total),
            "_sort": (y * 100) + m
        })
    history.sort(key=lambda x: x["_sort"])
    for h in history:
        h.pop("_sort", None)

    # MTD current_revenue per trade group = invoiced this month - credits on this month's invoices
    inv = filtered_dfs.get('invoices', pd.DataFrame())
    inv_mtd_tg: Dict[str, float] = {}
    if not inv.empty:
        inv_mtd = inv[(inv['year'] == cy) & (inv['month'] == cm)]
        for _, row in inv_mtd.iterrows():
            raw_trade = row.get('Job_Trade__c') or ''
            macro_group, _ = TRADE_REVERSE_MAP.get(raw_trade, ('Other', 'Other'))
            charge = float(row.get('Charge_Net__c', 0) or 0)
            inv_mtd_tg[macro_group] = inv_mtd_tg.get(macro_group, 0.0) + charge

    # Credits on this month's invoices, grouped by trade group
    cred_this_inv_tg: Dict[str, float] = {}
    if not cred.empty and 'invoice_date' in cred.columns and 'invoice_trade_group' in cred.columns:
        inv_dt = pd.to_datetime(cred['invoice_date'].str[:10], errors='coerce')
        cred_this_inv = cred[(inv_dt.dt.year == cy) & (inv_dt.dt.month == cm)]
        for _, row in cred_this_inv.iterrows():
            raw_trade = row.get('invoice_trade_group') or ''
            macro_group, _ = TRADE_REVERSE_MAP.get(raw_trade, ('Other', 'Other'))
            credit_amt = float(row.get('Charge_Net__c', 0) or 0)
            cred_this_inv_tg[macro_group] = cred_this_inv_tg.get(macro_group, 0.0) + credit_amt

    # current_revenue per trade group (matches main gauge denominator)
    current_rev_tg: Dict[str, float] = {
        k: max(0.0, inv_mtd_tg.get(k, 0.0) - cred_this_inv_tg.get(k, 0.0))
        for k in set(inv_mtd_tg) | set(cred_this_inv_tg)
    }

    all_groups = set(by_trade_group.keys()) | set(current_rev_tg.keys())
    by_trade_sorted = sorted(
        [{"name": k, "collected": _r(by_trade_group.get(k, 0.0)), "invoiced": _r(current_rev_tg.get(k, 0.0))}
         for k in all_groups if by_trade_group.get(k, 0.0) > 0],
        key=lambda x: x["collected"], reverse=True
    )
    return {
        "total": _r(total_mtd),
        "target": _r(3500000.0 / 1.2),
        "by_sector": [{"name": k, "value": _r(v)} for k, v in by_sector.items()],
        "by_trade_group": by_trade_sorted,
        "history": history,
    }


def compute_outstanding_aging(
    filtered_dfs: Dict[str, pd.DataFrame],
    today: Optional[date] = None,
) -> Dict[str, Any]:
    """Equivalent to SalesforceClient.get_outstanding_aging()."""
    if today is None:
        today = date.today()

    out = filtered_dfs.get('outstanding', pd.DataFrame())
    pay = filtered_dfs.get('payments', pd.DataFrame())

    aging_buckets: Dict[str, float] = {
        '<30 Days': 0.0, '30-60 Days': 0.0, '60-90 Days': 0.0,
        '90-120 Days': 0.0, '>120 Days': 0.0
    }
    type_buckets: Dict[str, float] = {
        'Cash': 0.0, 'Credit': 0.0, 'Key Account': 0.0, 'Insurance': 0.0
    }

    if out.empty:
        return {'buckets': aging_buckets, 'by_type': type_buckets, 'total': 0.0}

    # Build bad-debt credit map from payments
    credit_map: Dict[str, float] = {}
    if not pay.empty:
        bad_debt = pay[
            (pay.get('asp04__Payment_Route_Selected__c', pd.Series()) == 'Bad debt write off') |
            (pay['asp04__Amount__c'] < 0)
        ] if 'asp04__Payment_Route_Selected__c' in pay.columns else pay[pay['asp04__Amount__c'] < 0]
        if not bad_debt.empty and 'invoice_name' in bad_debt.columns:
            credit_map = bad_debt.groupby('invoice_name')['asp04__Amount__c'].apply(
                lambda x: x.abs().sum()
            ).to_dict()

    for _, inv in out.iterrows():
        name = inv.get('Name')
        acc_type = inv.get('account_type')
        drc_applies = bool(inv.get('drc_applies', False))

        charge_net = float(inv.get('Charge_Net__c', 0) or 0)
        sum_payments = float(inv.get('Sum_of_Payments__c', 0) or 0)
        int_owed = float(inv.get('Interest_Fee_Owed__c', 0) or 0)
        int_received = float(inv.get('Interest_Fee_Received__c', 0) or 0)
        credit_raw = credit_map.get(name, 0.0) if name else 0.0

        formula_result = (charge_net - credit_raw) - sum_payments + int_owed - int_received

        if drc_applies:
            final_outstanding = max(0.0, float(formula_result))
        else:
            final_outstanding = max(0.0, float(formula_result) / 1.2)

        if final_outstanding <= 0:
            continue

        if acc_type and acc_type in type_buckets:
            type_buckets[acc_type] += final_outstanding
        elif acc_type:
            if 'Credit' in acc_type:
                type_buckets['Credit'] += final_outstanding
            elif 'Key' in acc_type:
                type_buckets['Key Account'] += final_outstanding

        inv_date_raw = inv.get('Date__c')
        if not inv_date_raw:
            continue
        try:
            inv_date = datetime.strptime(str(inv_date_raw)[:10], "%Y-%m-%d").date()
            age_days = (today - inv_date).days
        except Exception:
            continue

        if age_days < 30:
            bucket_key = '<30 Days'
        elif age_days < 60:
            bucket_key = '30-60 Days'
        elif age_days < 90:
            bucket_key = '60-90 Days'
        elif age_days < 120:
            bucket_key = '90-120 Days'
        else:
            bucket_key = '>120 Days'

        aging_buckets[bucket_key] += final_outstanding

    for k in aging_buckets:
        aging_buckets[k] = _r(aging_buckets[k])
    for k in type_buckets:
        type_buckets[k] = _r(type_buckets[k])

    return {
        'buckets': aging_buckets,
        'by_type': type_buckets,
        'total': _r(sum(type_buckets.values())),
    }


def compute_ajv_trend(
    filtered_dfs: Dict[str, pd.DataFrame],
    today: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """Equivalent to SalesforceClient.get_ajv_trend()."""
    if today is None:
        today = date.today()

    inv = filtered_dfs.get('invoices', pd.DataFrame())
    sas = filtered_dfs.get('sas', pd.DataFrame())

    months_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # Gross invoiced per month (total invoiced, no credit deduction)
    sales_by_month: Dict[Tuple, float] = {}
    if not inv.empty and 'year' in inv.columns:
        for (y, m), grp in inv.groupby(['year', 'month']):
            sales_by_month[(int(y), int(m))] = float(grp['Charge_Net__c'].sum())

    # Distinct reactive jobs per month from SAs
    job_sets: Dict[Tuple, set] = {}
    if not sas.empty:
        reactive_sas = sas[sas['Job_Type__c'] == 'Reactive'] if 'Job_Type__c' in sas.columns else sas
        for _, row in reactive_sas.iterrows():
            job_num = row.get('Job_Number__c')
            y, m = row.get('year'), row.get('month')
            if not job_num or not y or not m:
                continue
            key = (int(y), int(m))
            if key not in job_sets:
                job_sets[key] = set()
            job_sets[key].add(job_num)

    trend = []
    all_keys = set(sales_by_month.keys()) | set(job_sets.keys())
    for (y, m) in all_keys:
        sales = sales_by_month.get((y, m), 0.0)
        cnt = len(job_sets.get((y, m), set()))
        if cnt > 0 and sales > 0:
            ajv = sales / cnt
            trend.append({
                "month": f"{months_names[m - 1]} {str(y)[-2:]}",
                "value": _r(ajv),
                "_sort": (y * 100) + m,
            })

    trend.sort(key=lambda x: x["_sort"])
    for t in trend:
        t.pop("_sort", None)
    return trend


def compute_productivity_by_sector(
    filtered_dfs: Dict[str, pd.DataFrame],
    today: Optional[date] = None,
) -> Dict[str, Any]:
    """Equivalent to SalesforceClient.get_productivity_by_sector()."""
    if today is None:
        today = date.today()
    cy, cm = today.year, today.month

    inv = filtered_dfs.get('invoices', pd.DataFrame())
    cred = filtered_dfs.get('credits', pd.DataFrame())

    inv_mtd = inv[(inv['year'] == cy) & (inv['month'] == cm)] if not inv.empty else pd.DataFrame()
    cred_mtd = cred[(cred['year'] == cy) & (cred['month'] == cm)] if not cred.empty else pd.DataFrame()

    job_types: Dict[str, Any] = {}
    type_trade_split: Dict[str, Any] = {}
    trades: Dict[str, Any] = {}

    for tg, sub_groups in TRADE_SUBGROUPS.items():
        trades[tg] = {"total": 0.0, "sub_trades": {sg: 0.0 for sg in sub_groups.keys()}}

    # Process invoices
    for _, rec in inv_mtd.iterrows():
        inv_name = rec.get('Name')
        j_type = rec.get('Type__c') or 'Unknown'
        charge = float(rec.get('Charge_Net__c', 0) or 0)

        if j_type not in job_types:
            job_types[j_type] = {"cnt": 0, "sales": 0.0}
            type_trade_split[j_type] = {tg: 0.0 for tg in TRADE_SUBGROUPS.keys()}
        job_types[j_type]["cnt"] += 1
        job_types[j_type]["sales"] += charge

        lookup = rec.get('Job_Trade__c')
        if lookup and lookup in TRADE_REVERSE_MAP:
            trade_group, sub_group = TRADE_REVERSE_MAP[lookup]
        else:
            trade_group = 'Other'
            sub_group = lookup or 'Unknown'

        if trade_group not in trades:
            trades[trade_group] = {"total": 0.0, "sub_trades": {}}
        trades[trade_group]["total"] += charge
        trades[trade_group]["sub_trades"][sub_group] = trades[trade_group]["sub_trades"].get(sub_group, 0.0) + charge

        if trade_group in type_trade_split.get(j_type, {}):
            type_trade_split[j_type][trade_group] = float(type_trade_split[j_type][trade_group]) + charge
        else:
            if j_type in type_trade_split:
                type_trade_split[j_type][trade_group] = charge

    # Subtract credits
    for _, cre in cred_mtd.iterrows():
        j_type = cre.get('invoice_type') or 'Unknown'
        credit_amt = float(cre.get('Charge_Net__c', 0) or 0)

        if j_type not in job_types:
            job_types[j_type] = {"cnt": 0, "sales": 0.0}
            type_trade_split[j_type] = {tg: 0.0 for tg in TRADE_SUBGROUPS.keys()}
        job_types[j_type]["sales"] -= credit_amt

        lookup = cre.get('invoice_trade_group')
        if lookup and lookup in TRADE_REVERSE_MAP:
            trade_group, sub_group = TRADE_REVERSE_MAP[lookup]
        else:
            trade_group = 'Other'
            sub_group = lookup or 'Unknown'

        if trade_group not in trades:
            trades[trade_group] = {"total": 0.0, "sub_trades": {}}
        trades[trade_group]["total"] -= credit_amt
        trades[trade_group]["sub_trades"][sub_group] = trades[trade_group]["sub_trades"].get(sub_group, 0.0) - credit_amt

        if j_type in type_trade_split:
            if trade_group not in type_trade_split[j_type]:
                type_trade_split[j_type][trade_group] = 0.0
            type_trade_split[j_type][trade_group] -= credit_amt

    job_types_list = [{"Job_Work_Type__c": k, "cnt": v["cnt"], "sales": _r(v["sales"])}
                      for k, v in job_types.items()]
    trades_list = []
    for k, v in trades.items():
        if k == 'Other':
            continue
        sub_trade_list = [{"name": st_k, "value": _r(st_v)} for st_k, st_v in v["sub_trades"].items()]
        trades_list.append({"Trade_Group__c": k, "total": _r(v["total"]), "sub_trades": sub_trade_list})

    return {"job_types": job_types_list, "trades": trades_list, "type_trade_split": type_trade_split}


def compute_sa_job_types(
    filtered_dfs: Dict[str, pd.DataFrame],
    today: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """Equivalent to SalesforceClient.get_sa_job_types()."""
    if today is None:
        today = date.today()
    cy, cm = today.year, today.month

    sas = filtered_dfs.get('sas', pd.DataFrame())
    if sas.empty:
        return []

    sas_mtd = sas[(sas['year'] == cy) & (sas['month'] == cm)]
    if sas_mtd.empty:
        return []

    counts: Dict[str, int] = {}
    type_trade_counts: Dict[str, Dict[str, int]] = {}
    seen_jobs: set = set()

    for _, rec in sas_mtd.iterrows():
        job_num = rec.get('Job_Number__c')
        if job_num and job_num in seen_jobs:
            continue
        if job_num:
            seen_jobs.add(job_num)
        jt = rec.get('Job_Type__c') or 'Unknown'
        counts[jt] = counts.get(jt, 0) + 1

        rt = rec.get('job_type_trade')
        trade_group = str(TRADE_REVERSE_MAP[rt][0]) if (rt and rt in TRADE_REVERSE_MAP) else 'Other'
        if jt not in type_trade_counts:
            type_trade_counts[jt] = {}
        type_trade_counts[jt][trade_group] = type_trade_counts[jt].get(trade_group, 0) + 1

    return [{"Job_Type__c": str(k), "cnt": int(v), "trade_counts": type_trade_counts.get(k, {})}
            for k, v in counts.items()]


def compute_sa_summary(
    filtered_dfs: Dict[str, pd.DataFrame],
    today: Optional[date] = None,
) -> Dict[str, Any]:
    """Equivalent to SalesforceClient.get_service_appointments_summary()."""
    if today is None:
        today = date.today()
    cy, cm = today.year, today.month
    thirty_days_ago = datetime.now() - timedelta(days=30)

    sas = filtered_dfs.get('sas', pd.DataFrame())

    empty_split = {'total': 0, 'new': 0, 'existing': 0, 'reactive': 0, 'fixed': 0, 'trades': []}
    if sas.empty or 'ActualStartTime' not in sas.columns:
        return {'today': empty_split, 'month': empty_split}

    # Parse datetime
    start_dt = pd.to_datetime(sas['ActualStartTime'].str[:19], errors='coerce')

    today_mask = start_dt.dt.date == today
    month_mask = (sas['year'] == cy) & (sas['month'] == cm)

    def _split(subset: pd.DataFrame) -> Dict[str, Any]:
        n_val, r_val, f_val, trades_map = 0, 0, 0, {}
        for _, rec in subset.iterrows():
            jt = rec.get('account_type')  # account_type field used for reactive/fixed in old code
            if jt == 'Reactive':
                r_val += 1
            elif jt == 'Fixed Price':
                f_val += 1

            rt = rec.get('job_type_trade')
            trade_group = str(TRADE_REVERSE_MAP[rt][0]) if (rt and rt in TRADE_REVERSE_MAP) else 'Other'
            trades_map[trade_group] = int(trades_map.get(trade_group, 0)) + 1

            c_raw = rec.get('account_created_date')
            if c_raw:
                try:
                    c_date = datetime.strptime(str(c_raw)[:19], '%Y-%m-%dT%H:%M:%S')
                    if c_date > thirty_days_ago:
                        n_val += 1
                except Exception:
                    pass

        return {
            'total': len(subset),
            'new': n_val,
            'existing': len(subset) - n_val,
            'reactive': r_val,
            'fixed': f_val,
            'trades': [{"name": k, "value": int(v)} for k, v in trades_map.items()]
        }

    today_sas = sas[today_mask]
    month_sas = sas[month_mask]
    return {'today': _split(today_sas), 'month': _split(month_sas)}


def compute_new_vs_existing(
    filtered_dfs: Dict[str, pd.DataFrame],
    today: Optional[date] = None,
) -> Dict[str, int]:
    """Equivalent to SalesforceClient.get_new_vs_existing_clients()."""
    if today is None:
        today = date.today()
    cy, cm = today.year, today.month

    sas = filtered_dfs.get('sas', pd.DataFrame())
    if sas.empty:
        return {'new': 0, 'existing': 0, 'total': 0, 'new_unique_accounts': 0}

    sas_mtd = sas[(sas['year'] == cy) & (sas['month'] == cm)]
    seen_jobs: set = set()
    seen_new_accounts: set = set()
    new_count = 0
    existing_count = 0

    for _, rec in sas_mtd.iterrows():
        job_num = rec.get('Job_Number__c')
        if job_num and job_num in seen_jobs:
            continue
        if job_num:
            seen_jobs.add(job_num)

        acc_name = rec.get('account_name')
        created_raw = rec.get('account_created_date')
        if created_raw:
            try:
                created = datetime.strptime(str(created_raw)[:10], '%Y-%m-%d')
                if created.year == cy and created.month == cm:
                    new_count += 1
                    if acc_name:
                        seen_new_accounts.add(acc_name)
                else:
                    existing_count += 1
            except Exception:
                existing_count += 1
        else:
            existing_count += 1

    return {
        'new': new_count,
        'existing': existing_count,
        'total': new_count + existing_count,
        'new_unique_accounts': len(seen_new_accounts),
    }


def compute_review_metrics(
    filtered_dfs: Dict[str, pd.DataFrame],
    today: Optional[date] = None,
) -> Dict[str, Any]:
    """Equivalent to SalesforceClient.get_review_metrics()."""
    if today is None:
        today = date.today()
    cy, cm = today.year, today.month

    sas = filtered_dfs.get('sas', pd.DataFrame())
    if sas.empty:
        return {"avg": 0, "count": 0}

    rated = sas[
        (sas['year'] == cy) &
        (sas['month'] == cm) &
        sas['Review_Star_Rating__c'].notna()
    ]
    if rated.empty:
        return {"avg": 0, "count": 0}
    # Deduplicate by SA Id
    if 'Id' in rated.columns:
        rated = rated.drop_duplicates('Id')
    avg = float(rated['Review_Star_Rating__c'].mean())
    return {"avg": _r(avg), "count": len(rated)}


def compute_insights(
    filtered_dfs: Dict[str, pd.DataFrame],
    today: Optional[date] = None,
) -> Dict[str, str]:
    """Equivalent to SalesforceClient.get_dynamic_insights(). No ThreadPoolExecutor needed."""
    if today is None:
        today = date.today()

    insights: Dict[str, str] = {}
    try:
        if today.month == 1:
            last_m_y, last_m_m = today.year - 1, 12
        else:
            last_m_y, last_m_m = today.year, today.month - 1

        current_day = today.day
        last_m_len = calendar.monthrange(last_m_y, last_m_m)[1]
        last_m_day = min(current_day, last_m_len)

        # Sales MTD this month vs last month same-day period
        inv = filtered_dfs.get('invoices', pd.DataFrame())
        if not inv.empty and 'year' in inv.columns:
            cy, cm = today.year, today.month
            # This month: just sum all so far (data is already MTD since cache is fresh)
            this_m_inv = inv[(inv['year'] == cy) & (inv['month'] == cm)]
            cv = float(this_m_inv['Charge_Net__c'].sum()) if not this_m_inv.empty else 0.0

            # Last month: filter by day <= last_m_day
            last_m_inv = inv[(inv['year'] == last_m_y) & (inv['month'] == last_m_m)]
            if not last_m_inv.empty and 'Date__c' in last_m_inv.columns:
                inv_day = pd.to_datetime(last_m_inv['Date__c'].str[:10], errors='coerce').dt.day
                last_m_inv = last_m_inv[inv_day <= last_m_day]
            pv = float(last_m_inv['Charge_Net__c'].sum()) if not last_m_inv.empty else 0.0

            if pv > 0:
                diff = cv - pv
                growth = (diff / pv) * 100.0
                growth_abs = abs(growth)
                insights["sales"] = f"MTD Revenue is {'up' if diff >= 0 else 'down'} {growth_abs:.1f}% compared to same period last month."
            else:
                insights["sales"] = "MTD Revenue tracking properly."
        else:
            insights["sales"] = "MTD Revenue tracking properly."

        # Collections
        col = compute_collections_data(filtered_dfs, today)
        total_collected = float(col.get("total", 0.0))

        # Last month collections up to same day
        pay = filtered_dfs.get('payments', pd.DataFrame())
        lc_val = 0.0
        if not pay.empty and 'asp04__Payment_Stage__c' in pay.columns:
            lc_pay = pay[
                (pay['asp04__Payment_Stage__c'] == 'Collected from customer') &
                (pay['year'] == last_m_y) & (pay['month'] == last_m_m)
            ]
            if not lc_pay.empty and 'asp04__Payment_Date__c' in lc_pay.columns:
                lc_day = pd.to_datetime(lc_pay['asp04__Payment_Date__c'].str[:10], errors='coerce').dt.day
                lc_pay = lc_pay[lc_day <= last_m_day]
            lc_val = float(lc_pay['asp04__Amount__c'].sum()) / 1.2 if not lc_pay.empty else 0.0

        insights["collections"] = (
            f"MTD Collections: £{total_collected / 1_000_000:.2f}M "
            f"({'up' if total_collected >= lc_val else 'down'} "
            f"{abs(((total_collected - lc_val) / lc_val) * 100 if lc_val > 0 else 0):.1f}% "
            f"vs £{lc_val / 1_000_000:.2f}M last month)."
        )

        # Job types
        jt_d = compute_sa_job_types(filtered_dfs, today)
        t_sa = sum(int(r.get('cnt', 0)) for r in jt_d)
        f_sa_val = next((int(r.get('cnt', 0)) for r in jt_d if r.get('Job_Type__c') == 'Fixed Price'), 0)
        insights["job_type"] = (
            f"Fixed-price contracts are driving {(f_sa_val / t_sa) * 100:.1f}% of volume."
            if t_sa > 0 else "Job type split stabilizing."
        )

        # Outstanding
        aging = compute_outstanding_aging(filtered_dfs, today)
        t_debt = aging.get("total", 0.0)
        under_30 = aging.get('buckets', {}).get('<30 Days', 0.0)
        insights["outstanding"] = (
            f"Cash represents {(under_30 / t_debt) * 100:.1f}% of receivables."
            if t_debt > 0 else "Aging buckets monitored."
        )

        # Top trade
        prod = compute_productivity_by_sector(filtered_dfs, today)
        tr_data = prod.get("trades", [])
        if tr_data:
            top_trade = max(tr_data, key=lambda x: float(x.get('total', 0.0)))
            insights["sas"] = f"Performance strong in {top_trade.get('Trade_Group__c', 'Main')}."
        else:
            insights["sas"] = "Performance trending positively."

        insights["collection_trend"] = (
            "Collections trending higher than last month." if total_collected > lc_val else "Insights"
        )
        insights["collection_total"] = f"We have made £{total_collected:,.2f} in collections so far this month."

        sa_s = compute_sa_summary(filtered_dfs, today)
        insights["sa_count"] = f"Completed {sa_s['month']['total']:,} service appointments so far."
        if sa_s['month'].get('trades'):
            top_t = max(sa_s['month']['trades'], key=lambda x: x['value'])
            insights["top_trade_sa"] = f"{top_t['name']} has the highest number of service appointments this month."
        else:
            insights["top_trade_sa"] = "Operational performance tracking properly."

        rev = compute_review_metrics(filtered_dfs, today)
        if rev["count"] > 0:
            status = 'excellent' if rev['avg'] >= 4.4 else 'strong' if rev['avg'] >= 4.0 else 'good'
            insights["review_rating"] = (
                f"We have {rev['count']} reviews this month. "
                f"The average review rating is {rev['avg']}.\nStatus: {status.capitalize()}"
            )
        else:
            insights["review_rating"] = "Feedback being collected."

    except Exception:
        import traceback
        traceback.print_exc()
        insights = {
            "sales": "Steady.", "collections": "Normal.", "job_type": "Balanced.",
            "outstanding": "Managed.", "sas": "Positive."
        }
    return insights
