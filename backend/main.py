from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from salesforce_client import sf_client

app = FastAPI(title="Sector Performance API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/stats/insights")
async def get_insights():
    try:
        return sf_client.get_dynamic_insights()
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
async def get_summary():
    try:
        sf_data = sf_client.get_summary_metrics()
        
        if sf_data and sf_data.get("invoices"):
            inv_total = sf_data["invoices"].get("total_sales", 0) or 0
            inv_count = sf_data["invoices"].get("cnt", 0) or 0
            cred_total = sf_data.get("credits", {}).get("total_credits", 0) or 0
            collected = sf_data.get("collections", {}).get("total_collected", 0) or 0
            
            net_sales = inv_total - cred_total
            # Outstanding for THIS MONTH is Net Sales minus Collections 
            month_outstanding = net_sales - collected
            
            return {
                "invoice_count": {"value": f"{inv_count:,}", "trend": "↑ Live", "sparkline": [40, 45, 42, 48, 50, 45, 55, 60, 58, 62, 65, 70]},
                "net_sales": {"value": f"£{net_sales:,.2f}", "trend": "↑ Live", "sparkline": [1.2, 1.4, 1.3, 1.6, 1.8, 1.7, 2.0, 2.2, 2.1, 2.3, 2.5, 2.2]},
                "outstanding_amount": {"value": f"£{month_outstanding:,.2f}", "trend": "MTD Balance", "sparkline": [900, 850, 880, 820, 800, 780, 810, 840, 820, 850, 880, 890]},
                "total_credit": {"value": f"£{cred_total:,.2f}", "trend": "MTD Credit", "sparkline": [100, 120, 110, 105, 115, 130, 125, 140, 135, 150, 145, 160]},
                "target": f"£{net_sales:,.0f}",
                "net_sales_raw": net_sales,
                "net_billed_raw": inv_total,
                "progress": int((collected / net_sales) * 100) if net_sales > 0 else 0
            }

    except Exception as e:
        print(f"SF Summary Error: {e}")
        import traceback
        traceback.print_exc()
        
    # Fallback
    return {
        "invoice_count": {"value": "3,819", "trend": "↑ Mock", "sparkline": [40, 45, 42, 48, 50, 45, 55, 60, 58, 62, 65, 70]},
        "net_sales": {"value": "£2,235,930.19", "trend": "↑ Mock", "sparkline": [1.2, 1.4, 1.3, 1.6, 1.8, 1.7, 2.0, 2.2, 2.1, 2.3, 2.5, 2.2]},
        "outstanding_amount": {"value": "£889,895.83", "trend": "↓ Mock", "sparkline": [900, 850, 880, 820, 800, 780, 810, 840, 820, 850, 880, 890]},
        "total_credit": {"value": "£120,450.00", "trend": "↑ Mock", "sparkline": [100, 120, 110, 105, 115, 130, 125, 140, 135, 150, 145, 160]},
        "target": "£1,200,000",
        "net_sales_raw": 889000,
        "net_billed_raw": 2235930.19,
        "progress": 74
    }

@app.get("/api/stats/sales")
async def get_sales_stats():
    try:
        sf_data = sf_client.get_sales_trend()
        monthly_data = []
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        
        # Map year/month to invoice/credit totals
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
            # Store sorting key as YYYYMM
            sort_key = (year * 100) + month_idx
            # Format for UI (e.g., 'Jan 25')
            yr_str = f"{year}"
            ui_date = f"{months[month_idx - 1]} {yr_str[-2:]}"  # type: ignore
            
            # NET SALES CALCULATION
            inv_v = float(vals.get("inv", 0) or 0)
            cred_v = float(vals.get("cred", 0) or 0)
            net_sales = round(inv_v - cred_v, 2)  # type: ignore
            
            monthly_data.append({
                "date": ui_date,
                "sales": net_sales,
                "target": 2500000.0,
                "_sort_key": sort_key
            })
            
            # Build Quarterly Data
            quarter_num = (month_idx - 1) // 3 + 1
            q_label = f"Q{quarter_num} {str(year)[-2:]}"  # type: ignore
            q_sort_key = (year * 10) + quarter_num
            
            if q_label not in quarterly_dict:
                quarterly_dict[q_label] = {
                    "date": q_label,
                    "sales": 0.0,
                    "target": 7500000.0,
                    "_sort_key": q_sort_key
                }
            quarterly_dict[q_label]["sales"] = round(float(quarterly_dict[q_label]["sales"]) + net_sales, 2)  # type: ignore
        
        # Sort chronologically by year then month
        monthly_data.sort(key=lambda x: x["_sort_key"])
        
        quarterly_data = list(quarterly_dict.values())
        quarterly_data.sort(key=lambda x: x["_sort_key"])
        
        # Final rounding and cleanup
        for item in monthly_data:
            item.pop("_sort_key", None)
        for item in quarterly_data:
            item["sales"] = round(float(item["sales"]), 2)  # type: ignore
            item.pop("_sort_key", None)
        
        if monthly_data:
            return {
                "today": "Live Trend",
                "monthly": monthly_data,
                "quarterly": quarterly_data,
                "trades": [
                    {"name": "Drainage", "value": 649745, "category": "Mechanical"},
                    {"name": "Electrical", "value": 412356, "category": "Electrical"},
                ],
            }
    except Exception as e:
        print(f"SF Sales Error: {e}")
        import traceback
        traceback.print_exc()
        
    return {
        "today": "£39,272",
        "monthly": [
            {"date": "Jan 26", "sales": 3800000, "target": 2500000, "anomaly": False},
            {"date": "Feb 26", "sales": 1200000, "target": 2500000, "note": "Seasonal Downtown", "anomaly": True},
        ],
        "quarterly": [
            {"date": "Q1 26", "sales": 5000000, "target": 7500000, "anomaly": True},
        ],
        "trades": [
            {"name": "Drainage", "value": 649745, "category": "Mechanical"},
        ],
    }

@app.get("/api/stats/jobs")
async def get_job_stats():
    try:
        review_data = sf_client.get_review_metrics()
        return {
            "arr": f"{review_data['avg']:.2f}",
            "review_count": str(review_data['count']),
            "ongoing_jobs": "£233,129.02",
            "types": [
                {"name": "Fixed Price", "value": 441},
                {"name": "Reactive", "value": 2163},
            ],
            "total_jobs": 2604
        }
    except Exception as e:
        print(f"Jobs Stats Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "arr": "4.22",
            "review_count": "82",
            "ongoing_jobs": "£233,129.02",
            "types": [
                {"name": "Fixed Price", "value": 441},
                {"name": "Reactive", "value": 2163},
            ],
            "total_jobs": 2604
        }

@app.get("/api/stats/collections")
async def get_collections():
    try:
        data = sf_client.get_collections_data()
        return data
    except Exception as e:
        print(f"Collections Endpoint Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "total": 0,
            "history": [
                {"month": "January 2026", "value": 2791200},
                {"month": "March 2026", "value": 2600000},
            ],
            "by_sector": [],
            "by_trade": [],
            "types": [
                {"name": "Fixed Price", "value": 607803},
                {"name": "Reactive", "value": 2304932},
            ]
        }

@app.get("/api/stats/outstanding")
async def get_outstanding():
    try:
        sf_data = sf_client.get_outstanding_aging()
        ajv_trend = sf_client.get_ajv_trend()
        
        # Return real data if available, even if buckets are empty
        if sf_data is not None:
            return {
                "aging": sf_data,
                "ajv": ajv_trend
            }
    except Exception as e:
        print(f"Aging Exception: {e}")
        import traceback
        traceback.print_exc()
        
    # Fallback data if Salesforce call fails
    return {
        "aging": {
            'buckets': {
                '<30 Days': 1800000,
                '30-60 Days': 0,
                '60-90 Days': 0,
                '90-120 Days': 0,
                '>120 Days': 0
            }, 
            'total': 1800000
        },
        "ajv": [{"month": "January 2026", "value": 704}]
    }

@app.get("/api/stats/sas")
async def get_sas_stats():
    try:
        sf_data = sf_client.get_productivity_by_sector()
        
        trade_data = []
        for rec in sf_data.get('trades', []):
            trade_grp = rec.get('Trade_Group__c') or 'Unknown'
            val = round(rec.get('total', 0) or 0, 2)  # type: ignore
            sub_trades = rec.get('sub_trades', [])
            for st in sub_trades:
                st["value"] = round(st.get("value", 0), 2)  # type: ignore
            trade_data.append({"name": trade_grp, "value": val, "sub_trades": sub_trades})
            
        job_types = []
        for rec in sf_data.get('job_types', []):
            jtype = rec.get('Job_Work_Type__c') or 'Unknown'
            cnt = rec.get('cnt', 0) or 0
            sales = rec.get('sales', 0) or 0
            job_types.append({"name": jtype, "value": cnt, "sales": sales})
            
        # New SA-based Job Type split for the Donut
        sa_data = sf_client.get_sa_job_types()
        sa_job_types = []
        for rec in sa_data:
            jtype = rec.get('Job_Type__c') or 'Unknown'
            cnt = rec.get('cnt', 0) or 0
            sa_job_types.append({"name": jtype, "value": cnt})

        if trade_data or job_types:
            # Get summary breakdown
            sa_summary = sf_client.get_service_appointments_summary()
            
            return {
                "today_total": sa_summary['today']['total'],
                "month_total": sa_summary['month']['total'],
                "summary": sa_summary,
                "by_trade": trade_data,
                "month_split": job_types,
                "sa_job_types": sa_job_types,
                "type_trade_split": sf_data.get('type_trade_split', {})
            }
    except Exception as e:
        print(f"Productivity Exception: {e}")
        import traceback
        traceback.print_exc()

    return {
        "today_total": 0,
        "month_total": 0,
        "summary": {
            "today": {"total": 0, "new": 0, "existing": 0},
            "month": {"total": 0, "new": 0, "existing": 0}
        },
        "by_trade": [{"name": "Mock Trade", "value": 900, "sub_trades": []}],
        "month_split": [],
        "sa_job_types": [],
        "type_trade_split": {}
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)