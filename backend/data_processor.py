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
        "Decoration": ["Decorating", "Plastering", "Tiling", "Wallpapering", "Multi", "Decoration", "Decoration Project"],
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
}

# Trades to exclude entirely (not mapped, not shown as "Other")
EXCLUDED_TRADES = {
    "Utilities", "Utilities - Blended - General Building", "Utilities - Blended - Drainage",
    "Utilities - Drying", "Utilities - Project Managment",
    "Utilities - Project - Building Fabric", "Utilities - Project - Leak Detection",
    "Utilities - Project - Drainage", "Utilities - Project - Electrical",
    "Utilities - Blended - Heating & Hot Water (Domestic)",
    "Utilities - Blended - Electrical",
    "Utilities - Project - Heating & Hot Water (Domestic)",
    "Utilities - Blended - Heating & Hot Water (Commercial)",
    "Utilities - Project - Air Con, Ventilation & Refrigeration",
    "Vehicle repair",
}

TRADE_REVERSE_MAP: Dict[str, Tuple[str, str]] = {}
for _macro, _subs in TRADE_SUBGROUPS.items():
    for _sub_name, _trades in _subs.items():
        for _t in _trades:
            TRADE_REVERSE_MAP[_t] = (_macro, _sub_name)

# Reverse mapping: subgroup name → parent trade group (for WIP filtering)
_SUBGROUP_TO_GROUP: Dict[str, str] = {}
for _group, _subs in TRADE_SUBGROUPS.items():
    for _sub_name in _subs:
        _SUBGROUP_TO_GROUP[_sub_name] = _group
# WIP uses "Multi" instead of "Multi Trades"
_SUBGROUP_TO_GROUP["Multi"] = "Building Fabric"


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
    trade_group: Optional[str] = None,
    trade_subgroup: Optional[str] = None,
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

    # --- Chargebacks ---
    chargebacks = wv.get('chargebacks', pd.DataFrame()).copy()
    if sectors and not chargebacks.empty and 'invoice_sector' in chargebacks.columns:
        chargebacks = chargebacks[chargebacks['invoice_sector'].isin(sectors)]

    # --- Payments (filter by invoice_sector and invoice_account_type) ---
    if sectors and not payments.empty and 'invoice_sector' in payments.columns:
        payments = payments[payments['invoice_sector'].isin(sectors)]
    if account_type and not payments.empty and 'invoice_account_type' in payments.columns:
        payments = payments[payments['invoice_account_type'].isin(account_type)]
    if homeowner_region and not payments.empty and 'region' in payments.columns:
        payments = payments[payments['region'].isin(homeowner_region)]

    # --- Service Appointments ---
    if sectors and not sas.empty and 'job_Sector_Type__c' in sas.columns:
        sas = sas[sas['job_Sector_Type__c'].isin(sectors)]
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

    # --- WIP ---
    wip = wv.get('wip', pd.DataFrame()).copy()
    if sectors and not wip.empty and 'Sector_Type__c' in wip.columns:
        wip = wip[wip['Sector_Type__c'].isin(sectors)]

    # --- Trade group / subgroup filtering ---
    if trade_group and trade_group in TRADE_SUBGROUPS:
        if trade_subgroup and trade_subgroup in TRADE_SUBGROUPS[trade_group]:
            allowed_trades = set(TRADE_SUBGROUPS[trade_group][trade_subgroup])
        else:
            allowed_trades = set()
            for sub_trades in TRADE_SUBGROUPS[trade_group].values():
                allowed_trades.update(sub_trades)

        # Invoices: Job_Trade__c
        if not invoices.empty and 'Job_Trade__c' in invoices.columns:
            invoices = invoices[invoices['Job_Trade__c'].isin(allowed_trades)]
        # Credits: invoice_trade_group
        if not credits.empty and 'invoice_trade_group' in credits.columns:
            credits = credits[credits['invoice_trade_group'].isin(allowed_trades)]
        # Chargebacks: invoice_trade_group
        if not chargebacks.empty and 'invoice_trade_group' in chargebacks.columns:
            chargebacks = chargebacks[chargebacks['invoice_trade_group'].isin(allowed_trades)]
        # Payments: invoice_trade_group
        if not payments.empty and 'invoice_trade_group' in payments.columns:
            payments = payments[payments['invoice_trade_group'].isin(allowed_trades)]
        # SAs: job_type_trade
        if not sas.empty and 'job_type_trade' in sas.columns:
            sas = sas[sas['job_type_trade'].isin(allowed_trades)]
        # Outstanding: Job_Trade__c
        if not outstanding.empty and 'Job_Trade__c' in outstanding.columns:
            outstanding = outstanding[outstanding['Job_Trade__c'].isin(allowed_trades)]
        # WIP: Trade_Group__c contains subgroup-level names (e.g. "Drainage", "Electrical", "Multi")
        if not wip.empty and 'Trade_Group__c' in wip.columns:
            wip = wip[wip['Trade_Group__c'].map(
                lambda x: _SUBGROUP_TO_GROUP.get(x, '') == trade_group
            )]

    return {
        'invoices': invoices.reset_index(drop=True),
        'credits': credits.reset_index(drop=True),
        'chargebacks': chargebacks.reset_index(drop=True),
        'payments': payments.reset_index(drop=True),
        'sas': sas.reset_index(drop=True),
        'outstanding': outstanding.reset_index(drop=True),
        'wip': wip.reset_index(drop=True),
    }


# ---------------------------------------------------------------------------
# Compute functions
# ---------------------------------------------------------------------------

def compute_wip(filtered_dfs: Dict[str, pd.DataFrame]) -> dict:
    """Work in progress: Charge_Net - (Charge_Deposit / 1.2), deduplicated on Job_Number__c."""
    wip = filtered_dfs.get('wip', pd.DataFrame())
    if wip.empty:
        return {'total': 0.0, 'job_count': 0, 'by_day': []}

    # Deduplicate on Job_Number__c
    if 'Job_Number__c' in wip.columns:
        wip = wip.drop_duplicates(subset='Job_Number__c', keep='first')

    charge_net = pd.to_numeric(wip['Charge_Net__c'], errors='coerce').fillna(0)
    charge_deposit = pd.to_numeric(wip['Charge_Deposit__c'], errors='coerce').fillna(0)
    wip['_wip_value'] = charge_net - (charge_deposit / 1.2)

    total = round(float(wip['_wip_value'].sum()), 2)

    # Group by scheduled end date
    wip['_date'] = pd.to_datetime(wip['SchedEndTime'], errors='coerce').dt.strftime('%Y-%m-%d')
    by_day = (
        wip.groupby('_date')
        .agg(value=('_wip_value', 'sum'), jobs=('Job_Number__c', 'count'))
        .reset_index()
        .rename(columns={'_date': 'date'})
        .sort_values('date')
    )
    by_day['value'] = by_day['value'].round(2)
    by_day_list = by_day.to_dict('records')

    return {'total': total, 'job_count': len(wip), 'by_day': by_day_list}


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

    # --- Credits this month (credit CreatedDate = this month) ---
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
    if not cred.empty and 'CreatedDate' in cred.columns:
        cred_today = cred[cred['CreatedDate'].astype(str).str[:10] == today_str]
        today_cred = float(cred_today['Charge_Net__c'].sum()) if not cred_today.empty else 0.0

    return {'invoices': _monthly(inv), 'credits': _monthly(cred), 'today_net': round(today_inv - today_cred, 2)}


def compute_daily_sales(
    filtered_dfs: Dict[str, pd.DataFrame],
    today: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """Return cumulative daily net sales (invoices - credits) for the current month."""
    if today is None:
        today = date.today()
    cy, cm = today.year, today.month

    inv = filtered_dfs.get('invoices', pd.DataFrame())
    cred = filtered_dfs.get('credits', pd.DataFrame())

    inv_mtd = inv[(inv['year'] == cy) & (inv['month'] == cm)] if not inv.empty else pd.DataFrame()
    cred_mtd = cred[(cred['year'] == cy) & (cred['month'] == cm)] if not cred.empty else pd.DataFrame()

    daily: Dict[int, float] = {}
    if not inv_mtd.empty and 'Date__c' in inv_mtd.columns:
        for _, row in inv_mtd.iterrows():
            d = pd.to_datetime(str(row['Date__c'])[:10], errors='coerce')
            if pd.notna(d):
                daily[d.day] = daily.get(d.day, 0.0) + float(row.get('Charge_Net__c', 0) or 0)

    if not cred_mtd.empty and 'CreatedDate' in cred_mtd.columns:
        for _, row in cred_mtd.iterrows():
            d = pd.to_datetime(str(row['CreatedDate'])[:10], errors='coerce')
            if pd.notna(d):
                daily[d.day] = daily.get(d.day, 0.0) - float(row.get('Charge_Net__c', 0) or 0)

    # Build cumulative array for each day up to today
    result = []
    cumulative = 0.0
    for day in range(1, today.day + 1):
        cumulative += daily.get(day, 0.0)
        result.append({"day": day, "cumulative": round(cumulative, 2)})

    return result


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
    cb = filtered_dfs.get('chargebacks', pd.DataFrame())

    if pay.empty:
        return {"total": 0.0, "target": _r(3500000.0 / 1.2), "by_sector": [], "history": []}

    collected_pay = pay[pay.get('asp04__Payment_Stage__c', pd.Series()) == 'Collected from customer'] if 'asp04__Payment_Stage__c' in pay.columns else pay.copy()

    # -- MTD: invoice_date=this month, payment_date=this month (no credit/chargeback subtraction) --
    mtd_pay = collected_pay.copy()
    if 'invoice_date' in mtd_pay.columns:
        inv_dt = pd.to_datetime(mtd_pay['invoice_date'].str[:10], errors='coerce')
        mtd_pay = mtd_pay[(inv_dt.dt.year == cy) & (inv_dt.dt.month == cm)]
    mtd_pay = mtd_pay[(mtd_pay['year'] == cy) & (mtd_pay['month'] == cm)]

    by_sector: Dict[str, float] = {}
    by_trade_group: Dict[str, float] = {}
    total_mtd = 0.0
    for _, row in mtd_pay.iterrows():
        amt = float(row.get('asp04__Amount__c', 0) or 0)
        sector = row.get('invoice_sector') or 'Unknown'
        net = amt / 1.2
        total_mtd += net
        by_sector[sector] = by_sector.get(sector, 0.0) + net
        raw_trade = row.get('invoice_trade_group') or ''
        if raw_trade not in EXCLUDED_TRADES:
            macro_group, _ = TRADE_REVERSE_MAP.get(raw_trade, ('Other', 'Other'))
            by_trade_group[macro_group] = by_trade_group.get(macro_group, 0.0) + net

    # -- Historical trend (rolling collections): subtract chargebacks by (year, month) --
    hist_cb_buckets: Dict[Tuple[int, int], float] = {}
    if not cb.empty:
        for _, row in cb.iterrows():
            y, m = row.get('year'), row.get('month')
            if y and m:
                bucket = (int(y), int(m))
                hist_cb_buckets[bucket] = hist_cb_buckets.get(bucket, 0.0) + (float(row.get('Amount__c', 0) or 0) / 1.2)

    hist_buckets: Dict[Tuple, float] = {}
    for _, row in collected_pay.iterrows():
        y, m = row.get('year'), row.get('month')
        amt = float(row.get('asp04__Amount__c', 0) or 0)
        if y and m:
            bucket = (int(y), int(m))
            hist_buckets[bucket] = hist_buckets.get(bucket, 0.0) + (amt / 1.2)

    # Subtract chargebacks from each month
    for bucket in hist_buckets:
        hist_buckets[bucket] -= hist_cb_buckets.get(bucket, 0.0)

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
            if raw_trade in EXCLUDED_TRADES:
                continue
            macro_group, _ = TRADE_REVERSE_MAP.get(raw_trade, ('Other', 'Other'))
            charge = float(row.get('Charge_Net__c', 0) or 0)
            inv_mtd_tg[macro_group] = inv_mtd_tg.get(macro_group, 0.0) + charge

    # Credits on this month's invoices, grouped by trade group
    cred = filtered_dfs.get('credits', pd.DataFrame())
    cred_this_inv_tg: Dict[str, float] = {}
    if not cred.empty and 'invoice_date' in cred.columns and 'invoice_trade_group' in cred.columns:
        inv_dt = pd.to_datetime(cred['invoice_date'].str[:10], errors='coerce')
        cred_this_inv = cred[(inv_dt.dt.year == cy) & (inv_dt.dt.month == cm)]
        for _, row in cred_this_inv.iterrows():
            raw_trade = row.get('invoice_trade_group') or ''
            if raw_trade in EXCLUDED_TRADES:
                continue
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


def compute_collections_by_region(
    filtered_dfs: Dict[str, pd.DataFrame],
    today: Optional[date] = None,
    trade_group: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Compute collected and invoiced (current revenue) by region for the selected trade group, current month."""
    from trade_mapping import (
        get_trade_group_phase, get_trade_group_regions,
        postcode_to_region_phase2, postcode_to_region_phase3,
    )

    if today is None:
        today = date.today()
    if not trade_group:
        return []

    phase = get_trade_group_phase(trade_group)
    regions = get_trade_group_regions(trade_group)
    if not regions:
        return []

    region_fn = postcode_to_region_phase2 if phase == 2 else postcode_to_region_phase3
    cy, cm = today.year, today.month

    # Collected by region: payments this month on this month's invoices
    collected_by_region: Dict[str, float] = {r: 0.0 for r in regions}
    pay = filtered_dfs.get('payments', pd.DataFrame())
    if not pay.empty and 'asp04__Payment_Stage__c' in pay.columns:
        mtd_pay = pay[pay['asp04__Payment_Stage__c'] == 'Collected from customer'].copy()
        if 'invoice_date' in mtd_pay.columns:
            inv_dt = pd.to_datetime(mtd_pay['invoice_date'].str[:10], errors='coerce')
            mtd_pay = mtd_pay[(inv_dt.dt.year == cy) & (inv_dt.dt.month == cm)]
        mtd_pay = mtd_pay[(mtd_pay['year'] == cy) & (mtd_pay['month'] == cm)]
        if not mtd_pay.empty and 'invoice_postcode' in mtd_pay.columns:
            mtd_pay['_region'] = mtd_pay['invoice_postcode'].apply(
                lambda pc: region_fn(str(pc) if pd.notna(pc) else '')
            )
            for r, grp in mtd_pay.groupby('_region'):
                if r in collected_by_region:
                    collected_by_region[r] += float(grp['asp04__Amount__c'].sum()) / 1.2

    # Invoiced (current revenue) by region: invoiced this month - credits on this month's invoices
    invoiced_by_region: Dict[str, float] = {r: 0.0 for r in regions}
    inv = filtered_dfs.get('invoices', pd.DataFrame())
    if not inv.empty and 'Site_Postal_Code__c' in inv.columns:
        inv_mtd = inv[(inv['year'] == cy) & (inv['month'] == cm)].copy()
        if not inv_mtd.empty:
            inv_mtd['_region'] = inv_mtd['Site_Postal_Code__c'].apply(
                lambda pc: region_fn(str(pc) if pd.notna(pc) else '')
            )
            for r, grp in inv_mtd.groupby('_region'):
                if r in invoiced_by_region:
                    invoiced_by_region[r] += float(grp['Charge_Net__c'].sum())

    cred = filtered_dfs.get('credits', pd.DataFrame())
    if not cred.empty and 'invoice_date' in cred.columns and 'invoice_postcode' in cred.columns:
        inv_dt = pd.to_datetime(cred['invoice_date'].str[:10], errors='coerce')
        cred_this = cred[(inv_dt.dt.year == cy) & (inv_dt.dt.month == cm)].copy()
        if not cred_this.empty:
            cred_this['_region'] = cred_this['invoice_postcode'].apply(
                lambda pc: region_fn(str(pc) if pd.notna(pc) else '')
            )
            for r, grp in cred_this.groupby('_region'):
                if r in invoiced_by_region:
                    invoiced_by_region[r] -= float(grp['Charge_Net__c'].sum())

    result = []
    for r in regions:
        result.append({
            "name": r,
            "collected": _r(collected_by_region[r]),
            "invoiced": _r(max(0.0, invoiced_by_region[r])),
        })
    return result


def compute_outstanding_aging(
    filtered_dfs: Dict[str, pd.DataFrame],
    today: Optional[date] = None,
    trade_group: Optional[str] = None,
) -> Dict[str, Any]:
    """Equivalent to SalesforceClient.get_outstanding_aging()."""
    from trade_mapping import (
        get_trade_group_phase, get_trade_group_regions,
        postcode_to_region_phase2, postcode_to_region_phase3,
    )
    if today is None:
        today = date.today()

    # Region mapping for invoice records
    _region_fn = None
    if trade_group:
        phase = get_trade_group_phase(trade_group)
        _regions = get_trade_group_regions(trade_group)
        if _regions:
            _region_fn = postcode_to_region_phase2 if phase == 2 else postcode_to_region_phase3

    out = filtered_dfs.get('outstanding', pd.DataFrame())
    pay = filtered_dfs.get('payments', pd.DataFrame())

    aging_buckets: Dict[str, float] = {
        '<30 Days': 0.0, '30-60 Days': 0.0, '60-90 Days': 0.0,
        '90-120 Days': 0.0, '>120 Days': 0.0
    }
    type_buckets: Dict[str, float] = {
        'Cash': 0.0, 'Credit': 0.0, 'Key Account': 0.0, 'Insurance': 0.0
    }

    invoice_details: Dict[str, List[Dict[str, Any]]] = {
        'Cash': [], 'Credit': [], 'Key Account': [], 'Insurance': []
    }
    bucket_invoices: Dict[str, List[Dict[str, Any]]] = {
        '<30 Days': [], '30-60 Days': [], '60-90 Days': [],
        '90-120 Days': [], '>120 Days': []
    }

    if out.empty:
        return {'buckets': aging_buckets, 'by_type': type_buckets, 'total': 0.0, 'invoices': invoice_details}

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
        balance_outstanding = float(inv.get('Balance_Outstanding__c', 0) or 0)

        if drc_applies:
            final_outstanding = max(0.0, balance_outstanding)
        else:
            final_outstanding = max(0.0, balance_outstanding / 1.2)

        if final_outstanding <= 0:
            continue

        # Determine the display type key
        type_key = None
        if acc_type and acc_type in type_buckets:
            type_key = acc_type
        elif acc_type:
            if 'Credit' in acc_type:
                type_key = 'Credit'
            elif 'Key' in acc_type:
                type_key = 'Key Account'

        inv_date_raw = inv.get('Date__c')
        if not inv_date_raw:
            continue
        try:
            inv_date = datetime.strptime(str(inv_date_raw)[:10], "%Y-%m-%d").date()

            # Cash: ages from invoice_date + 2 days (2-day grace period)
            # Credit: ages from last day of the month after invoice month
            is_credit = acc_type and 'Credit' in str(acc_type)
            if is_credit:
                # End of next month from invoice date
                if inv_date.month == 12:
                    deadline = date(inv_date.year + 1, 1, calendar.monthrange(inv_date.year + 1, 1)[1])
                else:
                    next_m = inv_date.month + 1
                    deadline = date(inv_date.year, next_m, calendar.monthrange(inv_date.year, next_m)[1])
                age_days = max(0, (today - deadline).days)
            else:
                # Cash: 2-day grace period
                age_start = inv_date + timedelta(days=2)
                age_days = max(0, (today - age_start).days)
        except Exception:
            continue

        # Only include invoices that have actually passed their grace/deadline period
        if age_days == 0:
            continue

        # Compute region for this invoice
        inv_region = ''
        if _region_fn:
            pc = inv.get('Site_Postal_Code__c')
            inv_region = _region_fn(str(pc) if pd.notna(pc) else '')

        # Now safe to count in type buckets and collect detail
        if type_key:
            type_buckets[type_key] += final_outstanding
            invoice_details[type_key].append({
                'name': name,
                'id': inv.get('Id') or '',
                'account_name': inv.get('account_name') or '',
                'date': str(inv_date_raw)[:10],
                'charge_net': _r(charge_net),
                'outstanding': _r(final_outstanding),
                'region': inv_region,
            })

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
        inv_record = {
            'name': name,
            'id': inv.get('Id') or '',
            'account_name': inv.get('account_name') or '',
            'date': str(inv_date_raw)[:10],
            'charge_net': _r(charge_net),
            'outstanding': _r(final_outstanding),
            'region': inv_region,
        }
        bucket_invoices[bucket_key].append(inv_record)

    for k in aging_buckets:
        aging_buckets[k] = _r(aging_buckets[k])
    for k in type_buckets:
        type_buckets[k] = _r(type_buckets[k])

    # Sort each type's and bucket's invoices by outstanding descending
    for k in invoice_details:
        invoice_details[k].sort(key=lambda x: x['outstanding'], reverse=True)
    for k in bucket_invoices:
        bucket_invoices[k].sort(key=lambda x: x['outstanding'], reverse=True)

    return {
        'buckets': aging_buckets,
        'by_type': type_buckets,
        'total': _r(sum(type_buckets.values())),
        'invoices': invoice_details,
        'bucket_invoices': bucket_invoices,
    }


def compute_outstanding_by_region(
    filtered_dfs: Dict[str, pd.DataFrame],
    today: Optional[date] = None,
    trade_group: Optional[str] = None,
) -> Dict[str, Any]:
    """Break down outstanding debt by region for both account type and aging buckets."""
    from trade_mapping import (
        get_trade_group_phase, get_trade_group_regions,
        postcode_to_region_phase2, postcode_to_region_phase3,
    )

    if today is None:
        today = date.today()
    if not trade_group:
        return {}

    phase = get_trade_group_phase(trade_group)
    regions = get_trade_group_regions(trade_group)
    if not regions:
        return {}

    region_fn = postcode_to_region_phase2 if phase == 2 else postcode_to_region_phase3
    out = filtered_dfs.get('outstanding', pd.DataFrame())
    pay = filtered_dfs.get('payments', pd.DataFrame())

    if out.empty:
        return {"regions": regions, "by_type": {}, "buckets": {}}

    # Build bad-debt credit map
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

    # {region: {type: amount}}  and  {region: {bucket: amount}}
    type_by_region: Dict[str, Dict[str, float]] = {r: {'Cash': 0.0, 'Credit': 0.0} for r in regions}
    bucket_by_region: Dict[str, Dict[str, float]] = {
        r: {'<30 Days': 0.0, '30-60 Days': 0.0, '60-90 Days': 0.0, '>90 Days': 0.0}
        for r in regions
    }

    pc_col = 'Site_Postal_Code__c'
    for _, inv in out.iterrows():
        acc_type = inv.get('account_type')
        drc_applies = bool(inv.get('drc_applies', False))
        balance_outstanding = float(inv.get('Balance_Outstanding__c', 0) or 0)

        if drc_applies:
            final_outstanding = max(0.0, balance_outstanding)
        else:
            final_outstanding = max(0.0, balance_outstanding / 1.2)

        if final_outstanding <= 0:
            continue

        # Determine type key (Cash or Credit only for this chart)
        if acc_type and 'Credit' in str(acc_type):
            type_key = 'Credit'
        elif acc_type == 'Cash':
            type_key = 'Cash'
        else:
            type_key = None

        inv_date_raw = inv.get('Date__c')
        if not inv_date_raw:
            continue
        try:
            inv_date = datetime.strptime(str(inv_date_raw)[:10], "%Y-%m-%d").date()
            is_credit = acc_type and 'Credit' in str(acc_type)
            if is_credit:
                if inv_date.month == 12:
                    deadline = date(inv_date.year + 1, 1, calendar.monthrange(inv_date.year + 1, 1)[1])
                else:
                    next_m = inv_date.month + 1
                    deadline = date(inv_date.year, next_m, calendar.monthrange(inv_date.year, next_m)[1])
                age_days = max(0, (today - deadline).days)
            else:
                age_start = inv_date + timedelta(days=2)
                age_days = max(0, (today - age_start).days)
        except Exception:
            continue

        if age_days == 0:
            continue

        # Map postcode to region
        pc = inv.get(pc_col)
        region = region_fn(str(pc) if pd.notna(pc) else '')
        if region not in type_by_region:
            continue

        if type_key and type_key in type_by_region[region]:
            type_by_region[region][type_key] += final_outstanding

        if age_days < 30:
            bucket_key = '<30 Days'
        elif age_days < 60:
            bucket_key = '30-60 Days'
        elif age_days < 90:
            bucket_key = '60-90 Days'
        else:
            bucket_key = '>90 Days'
        bucket_by_region[region][bucket_key] += final_outstanding

    # Round values
    for r in regions:
        for k in type_by_region[r]:
            type_by_region[r][k] = _r(type_by_region[r][k])
        for k in bucket_by_region[r]:
            bucket_by_region[r][k] = _r(bucket_by_region[r][k])

    return {"regions": regions, "by_type": type_by_region, "buckets": bucket_by_region}


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


def compute_ajv_by_trade_group(
    filtered_dfs: Dict[str, pd.DataFrame],
    today: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """Compute current month AJV per trade group."""
    if today is None:
        today = date.today()
    cy, cm = today.year, today.month

    inv = filtered_dfs.get('invoices', pd.DataFrame())
    sas = filtered_dfs.get('sas', pd.DataFrame())

    # Sales per trade group this month
    sales_tg: Dict[str, float] = {}
    inv_mtd = inv[(inv['year'] == cy) & (inv['month'] == cm)] if not inv.empty else pd.DataFrame()
    for _, row in inv_mtd.iterrows():
        raw_trade = row.get('Job_Trade__c') or ''
        if raw_trade in EXCLUDED_TRADES:
            continue
        macro, _ = TRADE_REVERSE_MAP.get(raw_trade, ('Other', 'Other'))
        charge = float(row.get('Charge_Net__c', 0) or 0)
        sales_tg[macro] = sales_tg.get(macro, 0.0) + charge

    # Reactive job count per trade group this month
    jobs_tg: Dict[str, set] = {}
    if not sas.empty:
        sas_mtd = sas[(sas['year'] == cy) & (sas['month'] == cm)]
        reactive = sas_mtd[sas_mtd['Job_Type__c'] == 'Reactive'] if 'Job_Type__c' in sas_mtd.columns else sas_mtd
        for _, row in reactive.iterrows():
            job_num = row.get('Job_Number__c')
            rt = row.get('job_type_trade') or ''
            if not job_num or rt in EXCLUDED_TRADES:
                continue
            macro = str(TRADE_REVERSE_MAP[rt][0]) if rt in TRADE_REVERSE_MAP else 'Other'
            if macro not in jobs_tg:
                jobs_tg[macro] = set()
            jobs_tg[macro].add(job_num)

    result = []
    for tg in TRADE_SUBGROUPS:
        sales = sales_tg.get(tg, 0.0)
        cnt = len(jobs_tg.get(tg, set()))
        ajv = round(sales / cnt, 2) if cnt > 0 else 0.0
        result.append({"name": tg, "ajv": ajv, "jobs": cnt})
    return result


def compute_ajv_trend_per_trade_group(
    filtered_dfs: Dict[str, pd.DataFrame],
    today: Optional[date] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Compute monthly AJV trend for each trade group (last ~15 months)."""
    if today is None:
        today = date.today()

    inv = filtered_dfs.get('invoices', pd.DataFrame())
    sas = filtered_dfs.get('sas', pd.DataFrame())
    months_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # Gross invoiced per (month, trade_group)
    sales_by: Dict[Tuple, Dict[str, float]] = {}
    if not inv.empty and 'year' in inv.columns:
        for _, row in inv.iterrows():
            raw_trade = row.get('Job_Trade__c') or ''
            if raw_trade in EXCLUDED_TRADES:
                continue
            macro, _ = TRADE_REVERSE_MAP.get(raw_trade, ('Other', 'Other'))
            y, m = int(row.get('year', 0)), int(row.get('month', 0))
            if y == 0 or m == 0:
                continue
            key = (y, m)
            if key not in sales_by:
                sales_by[key] = {}
            sales_by[key][macro] = sales_by[key].get(macro, 0.0) + float(row.get('Charge_Net__c', 0) or 0)

    # Reactive job counts per (month, trade_group)
    job_sets: Dict[Tuple, Dict[str, set]] = {}
    if not sas.empty:
        reactive = sas[sas['Job_Type__c'] == 'Reactive'] if 'Job_Type__c' in sas.columns else sas
        for _, row in reactive.iterrows():
            job_num = row.get('Job_Number__c')
            rt = row.get('job_type_trade') or ''
            y, m = row.get('year'), row.get('month')
            if not job_num or not y or not m or rt in EXCLUDED_TRADES:
                continue
            macro = str(TRADE_REVERSE_MAP[rt][0]) if rt in TRADE_REVERSE_MAP else 'Other'
            key = (int(y), int(m))
            if key not in job_sets:
                job_sets[key] = {}
            if macro not in job_sets[key]:
                job_sets[key][macro] = set()
            job_sets[key][macro].add(job_num)

    all_keys = set(sales_by.keys()) | set(job_sets.keys())
    result: Dict[str, List] = {tg: [] for tg in TRADE_SUBGROUPS}

    for (y, m) in sorted(all_keys):
        label = f"{months_names[m - 1]} {str(y)[-2:]}"
        sort_key = y * 100 + m
        for tg in TRADE_SUBGROUPS:
            sales = sales_by.get((y, m), {}).get(tg, 0.0)
            cnt = len(job_sets.get((y, m), {}).get(tg, set()))
            if cnt > 0 and sales > 0:
                result[tg].append({"month": label, "value": _r(sales / cnt)})

    return result


def compute_ajv_by_region(
    filtered_dfs: Dict[str, pd.DataFrame],
    today: Optional[date] = None,
    trade_group: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Compute AJV trend per region, using the appropriate phase mapping for the trade group."""
    from trade_mapping import (
        get_trade_group_phase, get_trade_group_regions,
        postcode_to_region_phase2, postcode_to_region_phase3,
    )

    if today is None:
        today = date.today()

    if not trade_group:
        return []

    phase = get_trade_group_phase(trade_group)
    regions = get_trade_group_regions(trade_group)
    if not regions:
        return []

    region_fn = postcode_to_region_phase2 if phase == 2 else postcode_to_region_phase3

    inv = filtered_dfs.get('invoices', pd.DataFrame())
    sas = filtered_dfs.get('sas', pd.DataFrame())

    months_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # Postcode column: invoices have Site_Postal_Code__c, SAs have PostalCode
    inv_pc_col = 'Site_Postal_Code__c'
    sa_pc_col = 'PostalCode'

    # --- Sales per (month, region) ---
    sales_by_mr: Dict[Tuple, float] = {}
    if not inv.empty and 'year' in inv.columns and inv_pc_col in inv.columns:
        inv_copy = inv.copy()
        inv_copy['_region'] = inv_copy[inv_pc_col].apply(
            lambda pc: region_fn(str(pc) if pd.notna(pc) else '')
        )
        for (y, m, r), grp in inv_copy.groupby(['year', 'month', '_region']):
            sales_by_mr[(int(y), int(m), r)] = float(grp['Charge_Net__c'].sum())

    # --- Reactive job count per (month, region) ---
    jobs_by_mr: Dict[Tuple, set] = {}
    if not sas.empty and sa_pc_col in sas.columns:
        reactive_sas = sas[sas['Job_Type__c'] == 'Reactive'] if 'Job_Type__c' in sas.columns else sas
        sa_copy = reactive_sas.copy()
        sa_copy['_region'] = sa_copy[sa_pc_col].apply(
            lambda pc: region_fn(str(pc) if pd.notna(pc) else '')
        )
        for _, row in sa_copy.iterrows():
            job_num = row.get('Job_Number__c')
            y, m, r = row.get('year'), row.get('month'), row.get('_region')
            if not job_num or not y or not m:
                continue
            key = (int(y), int(m), r)
            if key not in jobs_by_mr:
                jobs_by_mr[key] = set()
            jobs_by_mr[key].add(job_num)

    # Collect all (year, month) keys
    all_ym = set()
    for (y, m, _) in list(sales_by_mr.keys()) + list(jobs_by_mr.keys()):
        all_ym.add((y, m))

    # Build per-region trend
    result = []
    for region in regions:
        trend = []
        for (y, m) in all_ym:
            sales = sales_by_mr.get((y, m, region), 0.0)
            cnt = len(jobs_by_mr.get((y, m, region), set()))
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
        result.append({"region": region, "trend": trend})

    return result


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
        if lookup and lookup in EXCLUDED_TRADES:
            pass  # skip trade grouping for excluded trades
        elif lookup and lookup in TRADE_REVERSE_MAP:
            trade_group, sub_group = TRADE_REVERSE_MAP[lookup]
            if trade_group not in trades:
                trades[trade_group] = {"total": 0.0, "sub_trades": {}}
            trades[trade_group]["total"] += charge
            trades[trade_group]["sub_trades"][sub_group] = trades[trade_group]["sub_trades"].get(sub_group, 0.0) + charge
            if trade_group in type_trade_split.get(j_type, {}):
                type_trade_split[j_type][trade_group] = float(type_trade_split[j_type][trade_group]) + charge
            elif j_type in type_trade_split:
                type_trade_split[j_type][trade_group] = charge
        else:
            trade_group = 'Other'
            sub_group = lookup or 'Unknown'
            if trade_group not in trades:
                trades[trade_group] = {"total": 0.0, "sub_trades": {}}
            trades[trade_group]["total"] += charge
            trades[trade_group]["sub_trades"][sub_group] = trades[trade_group]["sub_trades"].get(sub_group, 0.0) + charge
            if trade_group in type_trade_split.get(j_type, {}):
                type_trade_split[j_type][trade_group] = float(type_trade_split[j_type][trade_group]) + charge
            elif j_type in type_trade_split:
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
        if lookup and lookup in EXCLUDED_TRADES:
            continue
        elif lookup and lookup in TRADE_REVERSE_MAP:
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


def compute_sales_by_region(
    filtered_dfs: Dict[str, pd.DataFrame],
    today: Optional[date] = None,
    trade_group: Optional[str] = None,
) -> Dict[str, Any]:
    """Compute net sales (invoices - credits) by region for the selected trade group, current month + past months."""
    from trade_mapping import (
        get_trade_group_phase, get_trade_group_regions,
        postcode_to_region_phase2, postcode_to_region_phase3,
    )

    if today is None:
        today = date.today()
    if not trade_group:
        return {}

    phase = get_trade_group_phase(trade_group)
    regions = get_trade_group_regions(trade_group)
    if not regions:
        return {}

    region_fn = postcode_to_region_phase2 if phase == 2 else postcode_to_region_phase3

    inv = filtered_dfs.get('invoices', pd.DataFrame())
    cred = filtered_dfs.get('credits', pd.DataFrame())
    inv_pc_col = 'Site_Postal_Code__c'

    months_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # Build per-month data
    by_month: Dict[Tuple, Dict[str, float]] = {}  # (y,m) -> {region: net_sales}

    if not inv.empty and 'year' in inv.columns and inv_pc_col in inv.columns:
        inv_copy = inv.copy()
        inv_copy['_region'] = inv_copy[inv_pc_col].apply(
            lambda pc: region_fn(str(pc) if pd.notna(pc) else '')
        )
        for (y, m, r), grp in inv_copy.groupby(['year', 'month', '_region']):
            if r not in regions:
                continue
            key = (int(y), int(m))
            if key not in by_month:
                by_month[key] = {reg: 0.0 for reg in regions}
            by_month[key][r] += float(grp['Charge_Net__c'].sum())

    if not cred.empty and 'year' in cred.columns and 'invoice_postcode' in cred.columns:
        cred_copy = cred.copy()
        cred_copy['_region'] = cred_copy['invoice_postcode'].apply(
            lambda pc: region_fn(str(pc) if pd.notna(pc) else '')
        )
        for (y, m, r), grp in cred_copy.groupby(['year', 'month', '_region']):
            if r not in regions:
                continue
            key = (int(y), int(m))
            if key not in by_month:
                by_month[key] = {reg: 0.0 for reg in regions}
            by_month[key][r] -= float(grp['Charge_Net__c'].sum())

    # Format: list of {month, regions: {region: value}}
    result = []
    for (y, m), rv in by_month.items():
        result.append({
            "month": f"{months_names[m - 1]} {str(y)[-2:]}",
            "month_key": f"{y}-{m:02d}",
            "_sort": (y * 100) + m,
            "regions": {r: _r(v) for r, v in rv.items()},
        })
    result.sort(key=lambda x: x["_sort"])
    for r in result:
        r.pop("_sort", None)

    return {"regions": regions, "by_month": result}


def compute_job_type_regional_split(
    filtered_dfs: Dict[str, pd.DataFrame],
    today: Optional[date] = None,
    trade_group: Optional[str] = None,
) -> Dict[str, Any]:
    """Compute job type counts and revenue by region for the selected trade group."""
    from trade_mapping import (
        get_trade_group_phase, get_trade_group_regions,
        postcode_to_region_phase2, postcode_to_region_phase3,
    )

    if today is None:
        today = date.today()
    if not trade_group:
        return {}

    phase = get_trade_group_phase(trade_group)
    regions = get_trade_group_regions(trade_group)
    if not regions:
        return {}

    region_fn = postcode_to_region_phase2 if phase == 2 else postcode_to_region_phase3
    cy, cm = today.year, today.month

    inv = filtered_dfs.get('invoices', pd.DataFrame())
    sas = filtered_dfs.get('sas', pd.DataFrame())
    cred = filtered_dfs.get('credits', pd.DataFrame())

    inv_pc_col = 'Site_Postal_Code__c'
    sa_pc_col = 'PostalCode'

    # --- Counts by region per job type (from SAs, deduplicated by Job_Number__c) ---
    counts_by_type: Dict[str, Dict[str, int]] = {}  # {job_type: {region: count}}
    seen_jobs: set = set()
    if not sas.empty and 'year' in sas.columns:
        sas_mtd = sas[(sas['year'] == cy) & (sas['month'] == cm)]
        if not sas_mtd.empty and sa_pc_col in sas_mtd.columns:
            for _, row in sas_mtd.iterrows():
                job_num = row.get('Job_Number__c')
                if job_num and job_num in seen_jobs:
                    continue
                if job_num:
                    seen_jobs.add(job_num)
                j_type = row.get('Job_Type__c') or 'Unknown'
                pc = row.get(sa_pc_col)
                region = region_fn(str(pc) if pd.notna(pc) else '')
                if region not in regions:
                    continue
                if j_type not in counts_by_type:
                    counts_by_type[j_type] = {r: 0 for r in regions}
                counts_by_type[j_type][region] = counts_by_type[j_type].get(region, 0) + 1

    # --- Revenue by region per job type (from invoices - credits) ---
    revenue_by_type: Dict[str, Dict[str, float]] = {}  # {job_type: {region: revenue}}
    if not inv.empty and 'year' in inv.columns and inv_pc_col in inv.columns:
        inv_mtd = inv[(inv['year'] == cy) & (inv['month'] == cm)]
        for _, row in inv_mtd.iterrows():
            j_type = row.get('Type__c') or 'Unknown'
            charge = float(row.get('Charge_Net__c', 0) or 0)
            pc = row.get(inv_pc_col)
            region = region_fn(str(pc) if pd.notna(pc) else '')
            if region not in regions:
                continue
            if j_type not in revenue_by_type:
                revenue_by_type[j_type] = {r: 0.0 for r in regions}
            revenue_by_type[j_type][region] = revenue_by_type[j_type].get(region, 0.0) + charge

    # Subtract credits
    if not cred.empty and 'year' in cred.columns:
        cred_mtd = cred[(cred['year'] == cy) & (cred['month'] == cm)]
        inv_pc_col_cred = 'invoice_postcode'
        if not cred_mtd.empty and inv_pc_col_cred in cred_mtd.columns:
            for _, row in cred_mtd.iterrows():
                j_type = row.get('invoice_type') or 'Unknown'
                credit_amt = float(row.get('Charge_Net__c', 0) or 0)
                pc = row.get(inv_pc_col_cred)
                region = region_fn(str(pc) if pd.notna(pc) else '')
                if region not in regions:
                    continue
                if j_type not in revenue_by_type:
                    revenue_by_type[j_type] = {r: 0.0 for r in regions}
                revenue_by_type[j_type][region] = revenue_by_type[j_type].get(region, 0.0) - credit_amt

    return {
        "regions": regions,
        "counts_by_type": counts_by_type,
        "revenue_by_type": {jt: {r: _r(v) for r, v in rv.items()} for jt, rv in revenue_by_type.items()},
    }


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
        if rt and rt in EXCLUDED_TRADES:
            trade_group = None
        else:
            trade_group = str(TRADE_REVERSE_MAP[rt][0]) if (rt and rt in TRADE_REVERSE_MAP) else 'Other'
        if trade_group:
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
            if not (rt and rt in EXCLUDED_TRADES):
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
    *,
    precomputed_collections: Optional[Dict] = None,
    precomputed_aging: Optional[Dict] = None,
    precomputed_productivity: Optional[Dict] = None,
    precomputed_sa_job_types: Optional[List] = None,
    precomputed_sa_summary: Optional[Dict] = None,
    precomputed_reviews: Optional[Dict] = None,
) -> Dict[str, str]:
    """Equivalent to SalesforceClient.get_dynamic_insights(). No ThreadPoolExecutor needed.
    Accepts pre-computed results to avoid redundant heavy computation."""
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

        # Collections — use pre-computed if available
        col = precomputed_collections if precomputed_collections is not None else compute_collections_data(filtered_dfs, today)
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

        # Job types — use pre-computed if available
        jt_d = precomputed_sa_job_types if precomputed_sa_job_types is not None else compute_sa_job_types(filtered_dfs, today)
        t_sa = sum(int(r.get('cnt', 0)) for r in jt_d)
        f_sa_val = next((int(r.get('cnt', 0)) for r in jt_d if r.get('Job_Type__c') == 'Fixed Price'), 0)
        insights["job_type"] = (
            f"Fixed-price contracts are driving {(f_sa_val / t_sa) * 100:.1f}% of volume."
            if t_sa > 0 else "Job type split stabilizing."
        )

        # Outstanding — use pre-computed if available
        aging = precomputed_aging if precomputed_aging is not None else compute_outstanding_aging(filtered_dfs, today)
        t_debt = aging.get("total", 0.0)
        under_30 = aging.get('buckets', {}).get('<30 Days', 0.0)
        insights["outstanding"] = (
            f"Cash represents {(under_30 / t_debt) * 100:.1f}% of receivables."
            if t_debt > 0 else "Aging buckets monitored."
        )

        # Top trade — use pre-computed if available
        prod = precomputed_productivity if precomputed_productivity is not None else compute_productivity_by_sector(filtered_dfs, today)
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

        sa_s = precomputed_sa_summary if precomputed_sa_summary is not None else compute_sa_summary(filtered_dfs, today)
        insights["sa_count"] = f"Completed {sa_s['month']['total']:,} service appointments so far."
        if sa_s['month'].get('trades'):
            top_t = max(sa_s['month']['trades'], key=lambda x: x['value'])
            insights["top_trade_sa"] = f"{top_t['name']} has the highest number of service appointments this month."
        else:
            insights["top_trade_sa"] = "Operational performance tracking properly."

        rev = precomputed_reviews if precomputed_reviews is not None else compute_review_metrics(filtered_dfs, today)
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
