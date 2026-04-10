import asyncio
import calendar
import os
from datetime import date, timedelta
from pathlib import Path
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import pandas as pd
import uvicorn
from salesforce_client import sf_client
from typing import Optional, Dict, Tuple
from world_view import WorldViewCache
from data_processor import (
    filter_dataframes,
    compute_sectors,
    compute_summary_metrics,
    compute_sales_trend,
    compute_collections_data,
    compute_daily_sales,
    compute_outstanding_aging,
    compute_ajv_trend,
    compute_ajv_by_trade_group,
    compute_ajv_trend_per_trade_group,
    compute_productivity_by_sector,
    compute_sa_job_types,
    compute_sa_summary,
    compute_new_vs_existing,
    compute_review_metrics,
    compute_insights,
    compute_wip,
    compute_ajv_by_region,
    compute_job_type_regional_split,
    compute_sales_by_region,
    compute_collections_by_region,
    compute_outstanding_by_region,
)
from trade_mapping import get_trade_group_phase, get_trade_group_regions

world_view_cache: Optional[WorldViewCache] = None


def _parse_sectors(sectors_param: Optional[str]) -> Optional[tuple]:
    if not sectors_param:
        return None
    return tuple(s.strip() for s in sectors_param.split(',') if s.strip())

def _parse_account_types(account_type_param: Optional[str]) -> Optional[tuple]:
    if not account_type_param:
        return None
    return tuple(s.strip() for s in account_type_param.split(',') if s.strip())

def _parse_homeowner_regions(homeowner_region_param: Optional[str]) -> Optional[tuple]:
    if not homeowner_region_param:
        return None
    return tuple(s.strip() for s in homeowner_region_param.split(',') if s.strip())


# ---------------------------------------------------------------------------
# Load sector targets from Excel — keyed by (year, month, sector, trade_group) → target
# ---------------------------------------------------------------------------
_TARGETS_FILE = Path(__file__).parent.parent / "Sector performance Targets.xlsx"
_sector_targets: Dict[Tuple[int, int, str, str], float] = {}

# Excel trade_group names → code trade_group names
_TRADE_GROUP_NORMALIZE = {
    'HVAC & Electrical': 'HVac & Electrical',
    'Leak,Damp & Restoration': 'Leak, Damp & Restoration',
}

def _load_targets():
    global _sector_targets
    if not _TARGETS_FILE.exists():
        print(f"[Targets] File not found: {_TARGETS_FILE}")
        return
    try:
        import datetime as _dt
        df = pd.read_excel(_TARGETS_FILE)
        df.columns = ['month_date', 'sector', 'v5', 'target', 'trade_group']
        # Excel parses DD/MM/YYYY dates as MM/DD — swap day↔month to correct
        df['month_date'] = df['month_date'].apply(
            lambda d: d.replace(month=d.day, day=d.month)
            if isinstance(d, _dt.datetime) and d.day <= 12 else d
        )
        df = df.dropna(subset=['month_date', 'sector', 'target'])
        for _, row in df.iterrows():
            tg_raw = str(row.get('trade_group', '')).strip()
            tg = _TRADE_GROUP_NORMALIZE.get(tg_raw, tg_raw)
            key = (int(row['month_date'].year), int(row['month_date'].month), str(row['sector']).strip(), tg)
            _sector_targets[key] = float(row['target'])
        print(f"[Targets] Loaded {len(_sector_targets)} sector-month-trade targets")
    except Exception as e:
        print(f"[Targets] Failed to load: {e}")

_load_targets()


_HOMEOWNER_REGION_PCTS: Dict[str, float] = {
    'North West': 0.33,
    'South West': 0.33,
    'East': 0.30,
    'Central': 0.04,
}

def _get_monthly_target(year: int, month: int, sectors=None, homeowner_regions=None, trade_group=None) -> float:
    """Sum targets for a given month, optionally filtered by sector, homeowner region, and trade group."""
    total = 0.0
    for (y, m, s, tg), val in _sector_targets.items():
        if y == year and m == month:
            if sectors is not None and s not in sectors:
                continue
            if trade_group is not None and tg != trade_group:
                continue
            if s == 'Home Owner' and homeowner_regions:
                region_pct = sum(_HOMEOWNER_REGION_PCTS.get(r, 0) for r in homeowner_regions)
                total += val * region_pct
            else:
                total += val
    return round(total, 0)


_SUB_PATH = os.getenv("APP_BASE_PATH", "")  # e.g. "/business-performance"

app = FastAPI(title="Sector Performance API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


_startup_error: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    global world_view_cache, _startup_error
    try:
        print("[Startup] Connecting to Salesforce...")
        sf = sf_client.sf
        print(f"[Startup] Connected to Salesforce: {sf.sf_instance}")
        world_view_cache = WorldViewCache(sf=sf)
        # Warm in background so the server starts listening immediately
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, world_view_cache.warm)
        print("[Startup] Cache warming in background...")
    except Exception as e:
        import traceback
        _startup_error = f"{type(e).__name__}: {e}"
        print(f"[Startup] FAILED: {_startup_error}")
        traceback.print_exc()


@app.get("/api/debug/startup-error")
async def debug_startup_error():
    return {"error": _startup_error, "cache_initialized": world_view_cache is not None}


@app.get("/api/debug/sf-test")
async def debug_sf_test():
    """Test a simple SOQL query to verify Salesforce connectivity."""
    try:
        sf = sf_client.sf
        result = sf.query("SELECT COUNT() FROM Customer_Invoice__c")
        return {"ok": True, "instance": sf.sf_instance, "result": result}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# Helpers: format raw compute output into the exact shapes the frontend expects
# ---------------------------------------------------------------------------

def _format_summary(sf_data):
    if sf_data and sf_data.get("invoices"):
        inv_total = sf_data["invoices"].get("total_sales", 0) or 0
        inv_count = sf_data["invoices"].get("cnt", 0) or 0
        cred_total = sf_data.get("credits", {}).get("total_credits", 0) or 0
        cred_this_inv = sf_data.get("credits", {}).get("credits_this_month_invoice", 0) or 0
        cred_prev_inv = sf_data.get("credits", {}).get("credits_prev_invoice", 0) or 0
        collected = sf_data.get("collections", {}).get("total_collected", 0) or 0

        net_sales = inv_total - cred_total
        current_revenue = inv_total - cred_this_inv
        month_outstanding = current_revenue - collected

        return {
            "invoice_count": {"value": f"{inv_count:,}", "trend": "↑ Live", "sparkline": [40, 45, 42, 48, 50, 45, 55, 60, 58, 62, 65, 70]},
            "net_sales": {"value": f"£{net_sales:,.0f}", "trend": "↑ Live", "sparkline": [1.2, 1.4, 1.3, 1.6, 1.8, 1.7, 2.0, 2.2, 2.1, 2.3, 2.5, 2.2]},
            "outstanding_amount": {"value": f"£{month_outstanding:,.0f}", "trend": "MTD Balance", "sparkline": [900, 850, 880, 820, 800, 780, 810, 840, 820, 850, 880, 890]},
            "total_credit": {"value": f"£{cred_total:,.0f}", "trend": "MTD Credit", "sparkline": [100, 120, 110, 105, 115, 130, 125, 140, 135, 150, 145, 160], "credits_this_invoice": cred_this_inv, "credits_prev_invoice": cred_prev_inv},
            "target": f"£{net_sales:,.0f}",
            "net_sales_raw": net_sales,
            "current_revenue_raw": current_revenue,
            "net_billed_raw": inv_total,
            "progress": int((collected / net_sales) * 100) if net_sales > 0 else 0
        }
    return {
        "invoice_count": {"value": "0", "trend": "↑ Live", "sparkline": []},
        "net_sales": {"value": "£0", "trend": "↑ Live", "sparkline": []},
        "outstanding_amount": {"value": "£0", "trend": "MTD Balance", "sparkline": []},
        "total_credit": {"value": "£0", "trend": "MTD Credit", "sparkline": []},
        "target": "£0",
        "net_sales_raw": 0,
        "current_revenue_raw": 0,
        "net_billed_raw": 0,
        "progress": 0
    }


def _format_sales(sf_data, sectors=None, homeowner_regions=None, trade_group=None):
    monthly_data = []
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    trend_map = {}

    for rec in sf_data.get('invoices', []):
        y, m = rec.get('year'), rec.get('month')
        if y and m:
            key = (y, m)
            if key not in trend_map:
                trend_map[key] = {"inv": 0, "cred": 0}
            trend_map[key]["inv"] = rec.get('total') or 0

    for rec in sf_data.get('credits', []):
        y, m = rec.get('year'), rec.get('month')
        if y and m:
            key = (y, m)
            if key not in trend_map:
                trend_map[key] = {"inv": 0, "cred": 0}
            trend_map[key]["cred"] = rec.get('total') or 0

    quarterly_dict = {}
    for (year, month_idx), vals in trend_map.items():
        sort_key = (year * 100) + month_idx
        yr_str = f"{year}"
        ui_date = f"{months[month_idx - 1]} {yr_str[-2:]}"
        inv_v = float(vals.get("inv", 0) or 0)
        cred_v = float(vals.get("cred", 0) or 0)
        net_sales = round(inv_v - cred_v, 0)

        month_target = _get_monthly_target(year, month_idx, sectors, homeowner_regions, trade_group=trade_group)
        monthly_data.append({"date": ui_date, "sales": net_sales, "target": month_target, "_sort_key": sort_key})

        quarter_num = (month_idx - 1) // 3 + 1
        q_label = f"Q{quarter_num} {str(year)[-2:]}"
        q_sort_key = (year * 10) + quarter_num
        if q_label not in quarterly_dict:
            quarterly_dict[q_label] = {"date": q_label, "sales": 0.0, "target": 0.0, "_sort_key": q_sort_key}
        quarterly_dict[q_label]["sales"] = round(float(quarterly_dict[q_label]["sales"]) + net_sales, 0)
        quarterly_dict[q_label]["target"] = round(float(quarterly_dict[q_label]["target"]) + month_target, 0)

    monthly_data.sort(key=lambda x: x["_sort_key"])
    quarterly_data = list(quarterly_dict.values())
    quarterly_data.sort(key=lambda x: x["_sort_key"])
    for item in monthly_data:
        item.pop("_sort_key", None)
    for item in quarterly_data:
        item["sales"] = round(float(item["sales"]), 0)
        item.pop("_sort_key", None)

    today_net = sf_data.get('today_net', 0.0)
    today_fmt = f"£{today_net:,.0f}" if today_net else "£0"
    if monthly_data:
        return {
            "today": today_fmt,
            "monthly": monthly_data,
            "quarterly": quarterly_data,
            "trades": [
                {"name": "Drainage", "value": 649745, "category": "Mechanical"},
                {"name": "Electrical", "value": 412356, "category": "Electrical"},
            ],
        }
    return {
        "today": today_fmt,
        "monthly": [],
        "quarterly": [],
        "trades": [],
    }


def _format_jobs(review_data, job_types_data):
    types = [{"name": jt['Job_Type__c'], "value": jt['cnt']} for jt in job_types_data]
    total = sum(jt['cnt'] for jt in job_types_data)
    return {
        "arr": f"{review_data['avg']:.2f}",
        "review_count": str(review_data['count']),
        "ongoing_jobs": "£233,129",
        "types": types,
        "total_jobs": total
    }


def _format_sas(sf_data, sa_data, sa_summary, client_split):
    trade_data = []
    for rec in sf_data.get('trades', []):
        trade_grp = rec.get('Trade_Group__c') or 'Unknown'
        val = round(rec.get('total', 0) or 0, 2)
        sub_trades = rec.get('sub_trades', [])
        for st in sub_trades:
            st["value"] = round(st.get("value", 0), 2)
        trade_data.append({"name": trade_grp, "value": val, "sub_trades": sub_trades})

    job_types = []
    for rec in sf_data.get('job_types', []):
        jtype = rec.get('Job_Work_Type__c') or 'Unknown'
        cnt = rec.get('cnt', 0) or 0
        sales = rec.get('sales', 0) or 0
        job_types.append({"name": jtype, "value": cnt, "sales": sales})

    sa_job_types = []
    sa_type_trade_counts = {}
    for rec in sa_data:
        jtype = rec.get('Job_Type__c') or 'Unknown'
        cnt = rec.get('cnt', 0) or 0
        sa_job_types.append({"name": jtype, "value": cnt})
        sa_type_trade_counts[jtype] = rec.get('trade_counts', {})

    return {
        "today_total": sa_summary['today']['total'],
        "month_total": sa_summary['month']['total'],
        "summary": sa_summary,
        "by_trade": trade_data,
        "month_split": job_types,
        "sa_job_types": sa_job_types,
        "sa_type_trade_counts": sa_type_trade_counts,
        "type_trade_split": sf_data.get('type_trade_split', {}),
        "client_split": client_split
    }


# ---------------------------------------------------------------------------
# Single /api/dashboard endpoint
# ---------------------------------------------------------------------------

@app.get("/api/trade-groups")
def get_trade_groups():
    from data_processor import TRADE_SUBGROUPS
    return {group: list(subs.keys()) for group, subs in TRADE_SUBGROUPS.items()}


_EMPTY_DASH = {"summary": None, "sales": [], "jobs": [], "collections": {}, "outstanding": {}, "sas": {}, "insights": {}, "wip": {}}


@app.get("/api/dashboard")
def get_dashboard(
    sectors: Optional[str] = Query(None),
    account_type: Optional[str] = Query(None),
    homeowner_region: Optional[str] = Query(None),
    trade_group: Optional[str] = Query(None),
    trade_subgroup: Optional[str] = Query(None),
):
    try:
        if world_view_cache is None:
            return JSONResponse(status_code=503, content={"error": "Cache not initialized.", "warming": True})
        wv = world_view_cache.get_world_view()
        if not wv:
            return JSONResponse(status_code=503, content={"error": "Cache is empty — data not yet loaded.", "warming": True})
        filtered = filter_dataframes(
            wv,
            sectors=_parse_sectors(sectors),
            account_type=_parse_account_types(account_type),
            homeowner_region=_parse_homeowner_regions(homeowner_region),
            trade_group=trade_group,
            trade_subgroup=trade_subgroup,
        )
        today = date.today()

        summary_raw = compute_summary_metrics(filtered, today)
        sales_raw = compute_sales_trend(filtered, today)
        collections = compute_collections_data(filtered, today)
        aging = compute_outstanding_aging(filtered, today, trade_group=trade_group)
        aging_regional = compute_outstanding_by_region(filtered, today, trade_group=trade_group)
        ajv = compute_ajv_trend(filtered, today)
        ajv_by_trade = compute_ajv_by_trade_group(filtered, today)
        ajv_trade_trends = compute_ajv_trend_per_trade_group(filtered, today)
        ajv_regional = compute_ajv_by_region(filtered, today, trade_group=trade_group)
        productivity = compute_productivity_by_sector(filtered, today)

        # Trade breakdown for past months (for month toggle)
        by_trade_by_month = {}
        for m_offset in range(0, 14):
            y = today.year
            m = today.month - m_offset
            while m < 1:
                m += 12
                y -= 1
            d = date(y, m, 1)
            key = f"{d.year}-{d.month:02d}"
            if key not in by_trade_by_month:
                prod_m = compute_productivity_by_sector(filtered, d)
                trades_m = []
                for rec in prod_m.get('trades', []):
                    tg = rec.get('Trade_Group__c') or 'Unknown'
                    val = round(rec.get('total', 0) or 0, 2)
                    subs = rec.get('sub_trades', [])
                    for st in subs:
                        st["value"] = round(st.get("value", 0), 2)
                    trades_m.append({"name": tg, "value": val, "sub_trades": subs})
                by_trade_by_month[key] = trades_m

        wip = compute_wip(filtered)
        sa_summary = compute_sa_summary(filtered, today)
        sa_job_types_data = compute_sa_job_types(filtered, today)
        job_type_regional = compute_job_type_regional_split(filtered, today, trade_group=trade_group)
        sales_by_region = compute_sales_by_region(filtered, today, trade_group=trade_group)
        collections_by_region = compute_collections_by_region(filtered, today, trade_group=trade_group)
        client_split = compute_new_vs_existing(filtered, today)
        reviews = compute_review_metrics(filtered, today)
        insights = compute_insights(
            filtered, today,
            precomputed_collections=collections,
            precomputed_aging=aging,
            precomputed_productivity=productivity,
            precomputed_sa_job_types=sa_job_types_data,
            precomputed_sa_summary=sa_summary,
            precomputed_reviews=reviews,
        )
        sectors_list = compute_sectors(filtered)
        daily_sales = compute_daily_sales(filtered, today)

        days_in_month = calendar.monthrange(today.year, today.month)[1]
        monthly_target = _get_monthly_target(
            today.year, today.month,
            sectors=_parse_sectors(sectors),
            homeowner_regions=_parse_homeowner_regions(homeowner_region),
            trade_group=trade_group,
        )

        # Regional target insight for trade group view
        if trade_group and monthly_target and monthly_target > 0:
            phase = get_trade_group_phase(trade_group)
            regions = get_trade_group_regions(trade_group)
            if regions:
                num_regions = len(regions)
                regional_target = monthly_target / num_regions
                # Expected pace through today
                expected_pct = today.day / days_in_month
                expected_regional = regional_target * expected_pct

                # Get current month regional sales from sales_by_region
                cm_key = f"{today.year}-{today.month:02d}"
                cm_data = {}
                for entry in (sales_by_region or {}).get("by_month", []):
                    if entry.get("month_key") == cm_key:
                        cm_data = entry.get("regions", {})
                        break

                parts = []
                for r in regions:
                    actual = cm_data.get(r, 0)
                    if expected_regional > 0:
                        pct_of_target = (actual / expected_regional) * 100
                        diff = actual - expected_regional
                        if diff >= 0:
                            parts.append(f"{r} is ahead of pace (£{actual/1000:.0f}K vs £{expected_regional/1000:.0f}K expected)")
                        else:
                            parts.append(f"{r} is behind pace (£{actual/1000:.0f}K vs £{expected_regional/1000:.0f}K expected)")

                if parts:
                    target_str = f"£{regional_target/1000:.0f}K"
                    insights["daily_target"] = (
                        f"Regional targets ({target_str} each): " + "; ".join(parts) + "."
                    )

        return {
            "summary": _format_summary(summary_raw),
            "sales": _format_sales(sales_raw, sectors=_parse_sectors(sectors), homeowner_regions=_parse_homeowner_regions(homeowner_region), trade_group=trade_group),
            "jobs": _format_jobs(reviews, sa_job_types_data),
            "collections": {**collections, "by_region": collections_by_region},
            "outstanding": {"aging": aging, "aging_regional": aging_regional, "ajv": ajv, "ajv_by_trade": ajv_by_trade, "ajv_trade_trends": ajv_trade_trends, "ajv_regional": ajv_regional},
            "sas": {**_format_sas(productivity, sa_job_types_data, sa_summary, client_split), "by_trade_by_month": by_trade_by_month, "job_type_regional": job_type_regional, "sales_by_region": sales_by_region},
            "wip": wip,
            "insights": insights,
            "sectors": sectors_list,
            "daily_target": {
                "daily_sales": daily_sales,
                "monthly_target": monthly_target,
                "days_in_month": days_in_month,
            },
        }
    except RuntimeError as e:
        return JSONResponse(status_code=503, content={"error": str(e), "warming": True})
    except Exception as e:
        print(f"Dashboard Error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Old endpoints — thin aliases over /api/dashboard
# ---------------------------------------------------------------------------

@app.get("/api/stats/sectors")
async def get_sectors():
    try:
        if world_view_cache is None:
            return JSONResponse(status_code=503, content={"error": "Cache not initialized", "warming": True})
        wv = world_view_cache.get_world_view()
        if not wv:
            return JSONResponse(status_code=503, content={"error": "Cache is empty", "warming": True})
        filtered = filter_dataframes(wv)
        return compute_sectors(filtered)
    except Exception as e:
        print(f"Sectors Error: {e}")
        return sf_client.get_distinct_sectors()


@app.get("/api/stats/insights")
async def get_insights(
    sectors: Optional[str] = Query(None),
    account_type: Optional[str] = Query(None),
    homeowner_region: Optional[str] = Query(None),
):
    try:
        result = await get_dashboard(sectors, account_type, homeowner_region)
        return result.get("insights", {})
    except Exception as e:
        print(f"Insights Endpoint Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "sales": "Revenue momentum remains steady across all channels.",
            "collections": "Collection efficiency is performing within expectations.",
            "job_type": "Job type distribution is balanced between Fixed and Reactive.",
            "outstanding": "Outstanding debt is being managed through proactive follow-ups.",
            "sas": "Secondary appointment performance is up across the main categories."
        }


@app.get("/api/stats/summary")
async def get_summary(
    sectors: Optional[str] = Query(None),
    account_type: Optional[str] = Query(None),
    homeowner_region: Optional[str] = Query(None),
):
    try:
        result = await get_dashboard(sectors, account_type, homeowner_region)
        return result.get("summary", {})
    except Exception as e:
        print(f"SF Summary Error: {e}")
        import traceback
        traceback.print_exc()
    return {
        "invoice_count": {"value": "3,819", "trend": "↑ Mock", "sparkline": [40, 45, 42, 48, 50, 45, 55, 60, 58, 62, 65, 70]},
        "net_sales": {"value": "£2,235,930", "trend": "↑ Mock", "sparkline": [1.2, 1.4, 1.3, 1.6, 1.8, 1.7, 2.0, 2.2, 2.1, 2.3, 2.5, 2.2]},
        "outstanding_amount": {"value": "£889,896", "trend": "↓ Mock", "sparkline": [900, 850, 880, 820, 800, 780, 810, 840, 820, 850, 880, 890]},
        "total_credit": {"value": "£120,450", "trend": "↑ Mock", "sparkline": [100, 120, 110, 105, 115, 130, 125, 140, 135, 150, 145, 160]},
        "target": "£1,200,000",
        "net_sales_raw": 889000,
        "net_billed_raw": 2235930.19,
        "progress": 74
    }


@app.get("/api/stats/sales")
async def get_sales_stats(
    sectors: Optional[str] = Query(None),
    account_type: Optional[str] = Query(None),
    homeowner_region: Optional[str] = Query(None),
):
    try:
        result = await get_dashboard(sectors, account_type, homeowner_region)
        return result.get("sales", {})
    except Exception as e:
        print(f"SF Sales Error: {e}")
        import traceback
        traceback.print_exc()
    return {
        "today": "£39,272",
        "monthly": [
            {"date": "Jan 26", "sales": 3800000, "target": 2500000, "anomaly": False},
        ],
        "quarterly": [],
        "trades": [],
    }


@app.get("/api/stats/jobs")
async def get_job_stats(
    sectors: Optional[str] = Query(None),
    account_type: Optional[str] = Query(None),
    homeowner_region: Optional[str] = Query(None),
):
    try:
        result = await get_dashboard(sectors, account_type, homeowner_region)
        return result.get("jobs", {})
    except Exception as e:
        print(f"Jobs Stats Error: {e}")
        import traceback
        traceback.print_exc()
    return {
        "arr": "4.22",
        "review_count": "82",
        "ongoing_jobs": "£233,129",
        "types": [
            {"name": "Fixed Price", "value": 441},
            {"name": "Reactive", "value": 2163},
        ],
        "total_jobs": 2604
    }


@app.get("/api/stats/collections")
async def get_collections(
    sectors: Optional[str] = Query(None),
    account_type: Optional[str] = Query(None),
    homeowner_region: Optional[str] = Query(None),
):
    try:
        result = await get_dashboard(sectors, account_type, homeowner_region)
        return result.get("collections", {})
    except Exception as e:
        print(f"Collections Endpoint Error: {e}")
        import traceback
        traceback.print_exc()
    return {
        "total": 0,
        "history": [],
        "by_sector": [],
        "by_trade": [],
        "types": []
    }


@app.get("/api/stats/outstanding")
async def get_outstanding(
    sectors: Optional[str] = Query(None),
    account_type: Optional[str] = Query(None),
    homeowner_region: Optional[str] = Query(None),
):
    try:
        result = await get_dashboard(sectors, account_type, homeowner_region)
        return result.get("outstanding", {})
    except Exception as e:
        print(f"Aging Exception: {e}")
        import traceback
        traceback.print_exc()
    return {
        "aging": {
            'buckets': {'<30 Days': 0, '30-60 Days': 0, '60-90 Days': 0, '90-120 Days': 0, '>120 Days': 0},
            'total': 0
        },
        "ajv": []
    }


@app.get("/api/stats/sas")
async def get_sas_stats(
    sectors: Optional[str] = Query(None),
    account_type: Optional[str] = Query(None),
    homeowner_region: Optional[str] = Query(None),
):
    try:
        result = await get_dashboard(sectors, account_type, homeowner_region)
        return result.get("sas", {})
    except Exception as e:
        print(f"Productivity Exception: {e}")
        import traceback
        traceback.print_exc()
    return {
        "today_total": 0, "month_total": 0,
        "summary": {"today": {"total": 0, "new": 0, "existing": 0}, "month": {"total": 0, "new": 0, "existing": 0}},
        "by_trade": [], "month_split": [], "sa_job_types": [], "type_trade_split": {}, "by_trade_by_month": {}
    }


# ---------------------------------------------------------------------------
# Debug endpoints
# ---------------------------------------------------------------------------

@app.get("/api/debug/world-view-status")
async def debug_world_view_status():
    """Show cache age, row counts, and refresh status."""
    if world_view_cache is None:
        return {"error": "cache not initialized"}
    return world_view_cache.get_status()


@app.get("/api/debug/sector-test")
async def debug_sector_test(sectors: Optional[str] = Query(None)):
    """Quick filter test using world view data."""
    parsed = _parse_sectors(sectors)
    try:
        wv = world_view_cache.get_world_view()
        filtered = filter_dataframes(wv, sectors=parsed)
        inv = filtered.get('invoices')
        return {
            "sectors_received": sectors,
            "sectors_parsed": list(parsed) if parsed else None,
            "invoice_count": len(inv) if inv is not None else 0,
        }
    except Exception as e:
        return {"sectors_received": sectors, "sectors_parsed": list(parsed) if parsed else None, "error": str(e)}


# Serve frontend static build
_STATIC_DIR = Path(__file__).parent / "static"
if _STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=_STATIC_DIR / "assets"), name="assets")

    # SPA catch-all: serve static file if it exists, otherwise index.html
    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        file_path = _STATIC_DIR / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_STATIC_DIR / "index.html")

# Mount under subpath for production (e.g. /business-performance)
if _SUB_PATH:
    root_app = FastAPI()

    # Re-register startup on root_app since mounted sub-app events don't propagate
    @root_app.on_event("startup")
    async def root_startup():
        await startup_event()

    @root_app.get("/")
    async def root_health():
        return {"status": "ok"}

    root_app.mount(_SUB_PATH, app)
    app = root_app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
