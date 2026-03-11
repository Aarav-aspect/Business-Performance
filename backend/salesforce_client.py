import os
import time
import threading
from functools import wraps
from typing import Any, Dict, List, Optional, Union, Tuple, cast
from concurrent.futures import ThreadPoolExecutor
from simple_salesforce import Salesforce
from dotenv import load_dotenv
from datetime import date, datetime, timedelta
import calendar

load_dotenv()

# Centralized Sector Filter String
SECTOR_FILTER = """
  'Agriculture', 'Central', 'Charity', 'Council offices', 'East', 'Education', 
  'Entertainment', 'Food and Beverage', 'Foreign Government', 'Healthcare', 
  'Home Owner C', 'Home Owner E', 'Home Owner NW', 'Home Owner SW', 'Hotels', 
  'Housing', 'Insurance Commercial', 'Insurance Domestic', 'Insurance Utilities', 
  'Manufacturing', 'NHS', 'North West', 'Office', 'Private Landlord', 'Property', 
  'Religious Buildings', 'Retail', 'Services', 'South West', 'Sports and Fitness'
"""

TRADE_SUBGROUPS = {
    "HVac & Electrical": {
        "Air Conditioning": ["Air Con, Ventilation & Refrigeration"],
        "Gas & Heating": ["Heating & Hot Water (Domestic)", "Heating & Hot Water (Commercial)", "Gas", "HVAC"],
        "Electrical": ["Electrical", "Electrical Renewable"],
    },
    "Building Fabric": {
        "Decoration": ["Decorating", "Plastering", "Tiling", "Wallpapering", "Multi", "Decoration"],
        "Roofing": ["Roofing/LeakDetection", "Roofing", "Roof Window & Gutter Cleaning"],
        "Multi Trades": ["Windows & Doors", "Handyman", "Carpentry", "Flooring Trade", "Fencing", "Brickwork & Paving", "Locksmithing", "Partition Walls & Ceilings", "Access", "Glazing"],
        "Project Management": ["Project Management Refurbishment", "General Refurbishment", "Bathroom Refurbishment", "Project Management Decoration"],
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
            "Leak Detection Diving"
        ],
        "Damp": ["Damp & Mould", "Damp Proofing", "Damp Survey", "Mould Survey", "Damp Survey Roofing", "Damp"],
        "Restoration": ["Drying", "LDR, Restoration", "Structural Drying & Certification"]
    },
    "Plumbing & Drainage": {
        "Plumbing": ["Plumbing", "Plumbing & Cold Water"],
        "Drainage": ["Drainage (Soil Water)", "Drainage (Wastewater)", "Drainage Restoration", "Drainage (Tanker)", "Commercial Pumps", "Drainage (Septic Tanks)", "Drainage", "Drainage Leak Detection"],
    },
    "Utilities": {
        "Utilities": ["Utilities", "Utilities - Blended - General Building", "Utilities - Blended - Drainage"]
    }
}

TRADE_REVERSE_MAP = {}
for macro_group, sub_groups in TRADE_SUBGROUPS.items():
    for sub_group_name, specific_trades in sub_groups.items():
        for sp in specific_trades:
            TRADE_REVERSE_MAP[sp] = (macro_group, sub_group_name)

_cache_lock = threading.Lock()

def simple_ttl_cache(ttl_seconds: int = 300):
    """Simple thread-safe memory cache decorator with TTL."""
    def decorator(func):
        cache: Dict[Tuple[Any, ...], Tuple[Any, float]] = {}
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Create a cache key from args and kwargs
            key = (args, tuple(sorted(kwargs.items())))
            now = time.time()
            with _cache_lock:
                if key in cache:
                    val, timestamp = cache[key]
                    if now - timestamp < ttl_seconds:
                        return val
            
            # Execute the actual function
            val = func(self, *args, **kwargs)
            
            with _cache_lock:
                cache[key] = (val, now)
            return val
        return wrapper
    return decorator

def _round(val: Any, ndigits: int = 2) -> float:
    """Helper to bypass broken type stubs for round() on some platforms."""
    try:
        return round(float(val), ndigits)  # type: ignore
    except:
        return 0.0

class SalesforceClient:
    def __init__(self):
        self.sf = Salesforce(
            username=os.getenv("SF_USERNAME"),
            password=os.getenv("SF_PASSWORD"),
            security_token=os.getenv("SF_SECURITY_TOKEN"),
            domain=os.getenv("SF_DOMAIN", "login")
        )

    @simple_ttl_cache(ttl_seconds=300)
    def get_summary_metrics(self) -> Dict[str, Any]:
        """Get summary metrics for the current month sales, credits, and collections."""
        inv_query = f"""
            SELECT COUNT(Id) cnt, SUM(Charge_Net__c) total_sales
            FROM Customer_Invoice__c 
            WHERE Date__c = THIS_MONTH AND Chumley_Test_Record__c = False
        """
        cred_query = f"""
            SELECT SUM(Amount__c) total_credits
            FROM Customer_Credit_Note__c 
            WHERE Date__c = THIS_MONTH
        """
        col_query = f"""
            SELECT SUM(Charge_Net__c) total_collected
            FROM Customer_Invoice__c 
            WHERE Date__c = THIS_MONTH AND Status__c = 'Paid'
        """
        
        try:
            inv_res = self.sf.query(inv_query)
            cred_res = self.sf.query(cred_query)
            col_res = self.sf.query(col_query)
            
            return {
                "invoices": inv_res['records'][0] if inv_res['records'] else {},
                "credits": cred_res['records'][0] if cred_res['records'] else {},
                "collections": col_res['records'][0] if col_res['records'] else {}
            }
        except Exception as e:
            print(f"Summary Query Error: {e}")
            return {"invoices": {}, "credits": {}, "collections": {}}

    @simple_ttl_cache(ttl_seconds=300)
    def get_sales_trend(self, period: str = 'monthly') -> Dict[str, List[Dict[str, Any]]]:
        """Get 14 months of rolling sales trend data."""
        inv_query = f"""
            SELECT CALENDAR_YEAR(Date__c) year, CALENDAR_MONTH(Date__c) month, SUM(Charge_Net__c) total 
            FROM Customer_Invoice__c 
            WHERE (Date__c = LAST_N_MONTHS:13 OR Date__c = THIS_MONTH) AND Chumley_Test_Record__c = False
            GROUP BY CALENDAR_YEAR(Date__c), CALENDAR_MONTH(Date__c)
        """
        cred_query = f"""
            SELECT CALENDAR_YEAR(Date__c) year, CALENDAR_MONTH(Date__c) month, SUM(Amount__c) total 
            FROM Customer_Credit_Note__c 
            WHERE (Date__c = LAST_N_MONTHS:13 OR Date__c = THIS_MONTH)
            GROUP BY CALENDAR_YEAR(Date__c), CALENDAR_MONTH(Date__c)
        """
        try:
            inv_res = self.sf.query(inv_query)
            cred_res = self.sf.query(cred_query)
            return {
                "invoices": inv_res.get('records', []),
                "credits": cred_res.get('records', [])
            }
        except Exception as e:
            print(f"Trend Query Error: {e}")
            return {"invoices": [], "credits": []}

    @simple_ttl_cache(ttl_seconds=300)
    def get_outstanding_aging(self) -> Dict[str, Any]:
        """Get outstanding debt grouped into aging buckets for the dashboard."""
        try:
            inv_query = """
                SELECT Name, Date__c, Charge_Net__c, Sum_of_Payments__c, 
                       Interest_Fee_Owed__c, Interest_Fee_Received__c, 
                       Account__r.Account_Type__c, Account__r.DRC_Applies__c,
                       Balance_Outstanding__c
                FROM Customer_Invoice__c
                WHERE Chumley_Test_Record__c = False 
                AND Date__c != NULL
                AND (Balance_Outstanding__c > 0 OR Interest_Fee_Owed__c > 0)
            """
            inv_results = self.sf.query_all(inv_query)
            invoices = inv_results.get('records', [])

            cred_query = """
                SELECT asp04__Amount__c, Customer_Invoice__r.Name 
                FROM asp04__Payment__c
                WHERE Customer_Invoice__c != NULL 
                AND (asp04__Payment_Route_Selected__c = 'Bad debt write off' OR asp04__Amount__c < 0)
            """
            cred_results = self.sf.query_all(cred_query)
            credits_data = cred_results.get('records', [])

            credit_map: Dict[str, float] = {}
            for cred in credits_data:
                inv_name = (cred.get('Customer_Invoice__r') or {}).get('Name')
                if inv_name:
                    amt = abs(cred.get('asp04__Amount__c') or 0)
                    credit_map[inv_name] = credit_map.get(inv_name, 0) + amt
            
            aging_buckets = {
                '<30 Days': 0.0,
                '30-60 Days': 0.0,
                '60-90 Days': 0.0,
                '90-120 Days': 0.0,
                '>120 Days': 0.0
            }
            type_buckets = {
                'Cash': 0.0,
                'Credit': 0.0,
                'Key Account': 0.0,
                'Insurance': 0.0
            }
            
            today_date = date.today()
            
            for inv in invoices:
                name = inv.get('Name')
                acc_type = (inv.get('Account__r') or {}).get('Account_Type__c')
                drc_applies = (inv.get('Account__r') or {}).get('DRC_Applies__c') or False
                
                charge_net = inv.get('Charge_Net__c') or 0
                sum_payments = inv.get('Sum_of_Payments__c') or 0
                int_owed = inv.get('Interest_Fee_Owed__c') or 0
                int_received = inv.get('Interest_Fee_Received__c') or 0
                credit_raw = credit_map.get(name, 0)

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
                    inv_date = datetime.strptime(inv_date_raw[:10], "%Y-%m-%d").date()
                    age_days = (today_date - inv_date).days
                except Exception:
                    continue
                
                if age_days < 30: bucket_key = '<30 Days'
                elif age_days < 60: bucket_key = '30-60 Days'
                elif age_days < 90: bucket_key = '60-90 Days'
                elif age_days < 120: bucket_key = '90-120 Days'
                else: bucket_key = '>120 Days'
                
                aging_buckets[bucket_key] += final_outstanding

            for k in aging_buckets: 
                aging_buckets[k] = _round(aging_buckets[k], 2)
            for k in type_buckets: 
                type_buckets[k] = _round(type_buckets[k], 2)

            return {
                'buckets': aging_buckets,
                'by_type': type_buckets,
                'total': _round(sum(type_buckets.values()), 2)
            }
        except Exception as e:
            print(f"Outstanding Categorization Error: {e}")
            return {'buckets': {}, 'total': 0}

    @simple_ttl_cache(ttl_seconds=300)
    def get_productivity_by_sector(self) -> Dict[str, Any]:
        """Group productivity and sales by sector and trade category."""
        query = f"""
            SELECT Type__c, Trade_Group_lookup__c, Sector_Type__c, Date__c, Charge_Net__c
            FROM Customer_Invoice__c 
            WHERE Date__c = THIS_MONTH 
            AND Chumley_Test_Record__c = False
        """
        try:
            res = self.sf.query(query)
            records = res.get('records', [])
            job_types: Dict[str, Any] = {}
            type_trade_split: Dict[str, Any] = {}
            trades: Dict[str, Any] = {}
            
            for tg, sub_groups in TRADE_SUBGROUPS.items():
                trades[tg] = {"total": 0.0, "sub_trades": {sg: 0.0 for sg in sub_groups.keys()}}
            
            for rec in records:
                j_type = rec.get('Type__c') or 'Unknown'
                charge = rec.get('Charge_Net__c') or 0.0
                if j_type not in job_types:
                    job_types[j_type] = {"cnt": 0, "sales": 0.0}
                    type_trade_split[j_type] = {tg: 0.0 for tg in TRADE_SUBGROUPS.keys()}
                job_types[j_type]["cnt"] += 1
                job_types[j_type]["sales"] += charge
                lookup = rec.get('Trade_Group_lookup__c')
                if lookup and lookup in TRADE_REVERSE_MAP:
                    trade_group, sub_group = TRADE_REVERSE_MAP[lookup]
                else:
                    trade_group = 'Other'
                    sub_group = lookup or 'Unknown'
                if trade_group not in trades:
                    trades[trade_group] = {"total": 0.0, "sub_trades": {}}
                trades[trade_group]["total"] += charge
                trades[trade_group]["sub_trades"][sub_group] = trades[trade_group]["sub_trades"].get(sub_group, 0.0) + charge
                if trade_group in type_trade_split[j_type]:
                    type_trade_split[j_type][trade_group] = float(type_trade_split[j_type][trade_group]) + charge
                else:
                    if trade_group not in type_trade_split[j_type]:
                        type_trade_split[j_type][trade_group] = 0.0
                    type_trade_split[j_type][trade_group] = float(type_trade_split[j_type][trade_group]) + charge
            
            job_types_list = [{"Job_Work_Type__c": k, "cnt": v["cnt"], "sales": _round(v["sales"], 2)} for k, v in job_types.items()]
            trades_list = []
            for k, v in trades.items():
                sub_trade_list = [{"name": st_k, "value": _round(st_v, 2)} for st_k, st_v in v["sub_trades"].items()]
                trades_list.append({"Trade_Group__c": k, "total": _round(v["total"], 2), "sub_trades": sub_trade_list})
            return {"job_types": job_types_list, "trades": trades_list, "type_trade_split": type_trade_split}
        except Exception as e:
            print(f"Productivity Query Error: {e}")
            return {"job_types": [], "trades": [], "type_trade_split": {}}

    @simple_ttl_cache(ttl_seconds=300)
    def get_review_metrics(self) -> Dict[str, Any]:
        """Aggregate review star ratings from service appointments related to this month's jobs."""
        try:
            job_id_query = "SELECT Job__c FROM Customer_Invoice__c WHERE Date__c = THIS_MONTH AND Job__c != NULL AND Chumley_Test_Record__c = False"
            job_res = self.sf.query_all(job_id_query)
            job_ids = list(set([r['Job__c'] for r in job_res.get('records', [])]))
            unique_ratings: Dict[str, float] = {}
            
            # Direct query for SAs this month
            direct_sa_query = "SELECT Id, Review_Star_Rating__c FROM ServiceAppointment WHERE ActualStartTime = THIS_MONTH AND Chumley_Test_Account__c = false AND Review_Star_Rating__c != NULL"
            direct_sa_res = self.sf.query_all(direct_sa_query)
            for r in direct_sa_res.get('records', []):
                try: unique_ratings[r['Id']] = float(r['Review_Star_Rating__c'])
                except: continue
            
            # Batch query for jobs
            chunk_size = 200
            for i in range(0, len(job_ids), chunk_size):
                chunk = job_ids[i:i + chunk_size]  # type: ignore
                id_str = ",".join([f"'{jid}'" for jid in chunk])
                sa_query = f"SELECT Id, Review_Star_Rating__c FROM ServiceAppointment WHERE Job__c IN ({id_str}) AND Chumley_Test_Account__c = false AND Review_Star_Rating__c != NULL"
                sa_res = self.sf.query_all(sa_query)
                for r in sa_res.get('records', []):
                    try: unique_ratings[r['Id']] = float(r['Review_Star_Rating__c'])
                    except: continue
                    
            ratings_list = list(unique_ratings.values())
            if not ratings_list: return {"avg": 0, "count": 0}
            mean = sum(ratings_list) / len(ratings_list)
            return {"avg": _round(mean, 2), "count": len(ratings_list)}
        except Exception as e:
            print(f"Review Metrics Error: {e}")
            return {"avg": 0, "count": 0}

    @simple_ttl_cache(ttl_seconds=300)
    def get_collections_data(self) -> Dict[str, Any]:
        """Aggregate collected payments and historical collection performance."""
        curr_query = "SELECT asp04__Amount__c, Customer_Invoice__r.Sector_Type__c, Customer_Invoice__r.Date__c FROM asp04__Payment__c WHERE asp04__Payment_Stage__c = 'Collected from customer' AND Customer_Invoice__r.Date__c = THIS_MONTH"
        hist_query = "SELECT CALENDAR_YEAR(asp04__Payment_Date__c) year, CALENDAR_MONTH(asp04__Payment_Date__c) month, SUM(asp04__Amount__c) total FROM asp04__Payment__c WHERE asp04__Payment_Stage__c = 'Collected from customer' AND (asp04__Payment_Date__c = LAST_N_MONTHS:13 OR asp04__Payment_Date__c = THIS_MONTH) GROUP BY CALENDAR_YEAR(asp04__Payment_Date__c), CALENDAR_MONTH(asp04__Payment_Date__c)"
        try:
            curr_res = self.sf.query(curr_query)
            curr_records = curr_res.get('records', [])
            by_sector: Dict[str, float] = {}
            total_collected_this_month = 0.0
            for rec in curr_records:
                amt = rec.get('asp04__Amount__c') or 0.0
                sector = (rec.get('Customer_Invoice__r') or {}).get('Sector_Type__c') or 'Unknown'
                total_collected_this_month += (amt / 1.2)
                by_sector[sector] = by_sector.get(sector, 0.0) + (amt / 1.2)
                
            hist_res = self.sf.query(hist_query)
            months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
            history = []
            for rec in hist_res.get('records', []):
                y, m = rec.get('year'), rec.get('month')
                if y and m:
                    history.append({
                        "month": f"{months[m-1]} {y}", 
                        "value": _round((rec.get('total') or 0.0) / 1.2, 2), 
                        "_sort": (y * 100) + m
                    })
            history.sort(key=lambda x: x["_sort"])
            for h in history: 
                h.pop("_sort", None)
            
            return {
                "total": _round(total_collected_this_month, 2), 
                "target": _round(3500000.0 / 1.2, 2), 
                "by_sector": [{"name": k, "value": _round(v, 2)} for k, v in by_sector.items()], 
                "history": history
            }
        except Exception as e:
            print(f"Collections Combined Query Error: {e}")
            return {"total": 0, "target": 0, "by_sector": [], "history": []}

    @simple_ttl_cache(ttl_seconds=300)
    def get_sa_job_types(self) -> List[Dict[str, Any]]:
        """Get counts of service appointments by job type for this month."""
        query = "SELECT Job_Type__c FROM ServiceAppointment WHERE ActualStartTime = THIS_MONTH"
        try:
            res = self.sf.query(query)
            records = res.get('records', [])
            counts: Dict[str, int] = {}
            for rec in records:
                jt = rec.get('Job_Type__c') or 'Unknown'
                counts[jt] = counts.get(jt, 0) + 1
            return [{"Job_Type__c": str(k), "cnt": int(v)} for k, v in counts.items()]
        except Exception as e:
            print(f"SA Job Type Query Error: {e}")
            return []

    @simple_ttl_cache(ttl_seconds=300)
    def get_service_appointments_summary(self) -> Dict[str, Any]:
        """Summarize service appointments for today and the current month."""
        try:
            today_date = date.today()
            t_start = f"{today_date.isoformat()}T00:00:00Z"
            t_end = f"{today_date.isoformat()}T23:59:59Z"
            m_start = f"{today_date.replace(day=1).isoformat()}T00:00:00Z"
            thirty_days_ago = datetime.now() - timedelta(days=30)
            
            t_query = f"SELECT Id, Job__r.Account__r.CreatedDate, Job__r.Account_Type__c FROM ServiceAppointment WHERE ActualStartTime >= {t_start} AND ActualStartTime <= {t_end} AND Chumley_Test_Account__c = false"
            m_query = f"SELECT Id, Job__r.Account__r.CreatedDate, Job__r.Account_Type__c, Job__r.Job_Type_Trade__c FROM ServiceAppointment WHERE ActualStartTime >= {m_start} AND ActualStartTime <= {t_end} AND Chumley_Test_Account__c = false"
            
            t_res = self.sf.query_all(t_query).get('records', [])
            m_res = self.sf.query_all(m_query).get('records', [])
            
            def split(records_in: List[Any]) -> Dict[str, Any]:
                n_val, r_val, f_val, trades_map = 0, 0, 0, {}
                for rec in records_in:
                    job = rec.get('Job__r') or {}
                    acc = job.get('Account__r') or {}
                    jt = job.get('Account_Type__c')
                    if jt == 'Reactive': 
                        r_val += 1  # type: ignore
                    elif jt == 'Fixed Price': 
                        f_val += 1  # type: ignore
                    
                    rt = job.get('Job_Type_Trade__c')
                    trade_group = str(TRADE_REVERSE_MAP[rt][0]) if (rt and rt in TRADE_REVERSE_MAP) else 'Other'
                    trades_map[trade_group] = int(trades_map.get(trade_group, 0)) + 1  # type: ignore
                    
                    c_raw = acc.get('CreatedDate')
                    if c_raw:
                        try:
                            c_date = datetime.strptime(str(c_raw)[:19], '%Y-%m-%dT%H:%M:%S')  # type: ignore
                            if c_date > thirty_days_ago: 
                                n_val += 1  # type: ignore
                        except: 
                            pass
                return {
                    'total': len(records_in), 
                    'new': n_val, 
                    'existing': len(records_in) - n_val,  # type: ignore
                    'reactive': r_val, 
                    'fixed': f_val, 
                    'trades': [{"name": k, "value": int(v)} for k, v in trades_map.items()]
                }
            
            return {'today': split(t_res), 'month': split(m_res)}
        except Exception as e:
            print(f"SA Summary Error: {e}")
            return {'today': {'total': 0, 'new': 0, 'existing': 0, 'reactive': 0, 'fixed': 0, 'trades': []}, 
                    'month': {'total': 0, 'new': 0, 'existing': 0, 'reactive': 0, 'fixed': 0, 'trades': []}}

    @simple_ttl_cache(ttl_seconds=300)
    def get_ajv_trend(self) -> List[Dict[str, Any]]:
        """Calculate the 14-month rolling Average Job Value (AJV) for Reactive jobs."""
        query = """
            SELECT CALENDAR_YEAR(Date__c) year, CALENDAR_MONTH(Date__c) month, 
                   SUM(Charge_Net__c) total_sales, COUNT(Id) job_count
            FROM Customer_Invoice__c 
            WHERE (Date__c = LAST_N_MONTHS:13 OR Date__c = THIS_MONTH)
            AND Type__c = 'Reactive'
            AND Chumley_Test_Record__c = False
            GROUP BY CALENDAR_YEAR(Date__c), CALENDAR_MONTH(Date__c)
        """
        try:
            res = self.sf.query(query)
            records = res.get('records', [])
            months_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
            
            trend = []
            for r in records:
                y = r.get('year')
                m = r.get('month')
                sales = r.get('total_sales') or 0.0
                cnt = r.get('job_count') or 0
                
                if y and m and cnt > 0:
                    ajv = (float(sales) / 1.2) / float(cnt)
                    trend.append({
                        "month": f"{months_names[m-1]} {y}",
                        "value": _round(ajv, 2),
                        "_sort": (y * 100) + m
                    })
            
            trend.sort(key=lambda x: x["_sort"])
            for t in trend: 
                t.pop("_sort", None)
            return trend
        except Exception as e:
            print(f"AJV Trend Error: {e}")
            return []

    def get_dynamic_insights(self) -> Dict[str, str]:
        """Generate AI-like insights by analyzing multiple data points in parallel."""
        insights: Dict[str, str] = {}
        try:
            today_date = date.today()
            current_day = datetime.now().day
            
            if today_date.month == 1: 
                last_m_y, last_m_m = today_date.year - 1, 12
            else: 
                last_m_y, last_m_m = today_date.year, today_date.month - 1
            
            last_m_len = calendar.monthrange(last_m_y, last_m_m)[1]
            last_m_day = min(current_day, last_m_len)
            last_m_mtd_end = datetime(last_m_y, last_m_m, last_m_day)
            
            q_this_s = today_date.replace(day=1).strftime('%Y-%m-%d')
            q_this_e = today_date.strftime('%Y-%m-%d')
            q_last_s = date(last_m_y, last_m_m, 1).strftime('%Y-%m-%d')
            q_last_mtd_e = last_m_mtd_end.strftime('%Y-%m-%d')
            
            s_query = f"""
                SELECT SUM(Charge_Net__c) total, CALENDAR_YEAR(Date__c) year, CALENDAR_MONTH(Date__c) month 
                FROM Customer_Invoice__c 
                WHERE ((Date__c >= {q_this_s} AND Date__c <= {q_this_e}) 
                   OR (Date__c >= {q_last_s} AND Date__c <= {q_last_mtd_e})) 
                AND Chumley_Test_Record__c = False 
                GROUP BY CALENDAR_YEAR(Date__c), CALENDAR_MONTH(Date__c)
            """
            lc_query = f"""
                SELECT SUM(asp04__Amount__c) total 
                FROM asp04__Payment__c 
                WHERE asp04__Payment_Stage__c = 'Collected from customer' 
                AND asp04__Payment_Date__c >= {q_last_s} 
                AND asp04__Payment_Date__c <= {q_last_mtd_e}
            """

            with ThreadPoolExecutor(max_workers=10) as executor:
                f_s = executor.submit(self.sf.query, s_query)  # type: ignore
                f_lc = executor.submit(self.sf.query, lc_query)  # type: ignore
                f_cd = executor.submit(self.get_collections_data)  # type: ignore
                f_sm = executor.submit(self.get_summary_metrics)  # type: ignore
                f_jt = executor.submit(self.get_sa_job_types)  # type: ignore
                f_ag = executor.submit(self.get_outstanding_aging)  # type: ignore
                f_pb = executor.submit(self.get_productivity_by_sector)  # type: ignore
                f_ss = executor.submit(self.get_service_appointments_summary)  # type: ignore
                f_rv = executor.submit(self.get_review_metrics)  # type: ignore
                
                s_res = f_s.result()
                lc_res = f_lc.result()
                col = f_cd.result()
                sum_m = f_sm.result()
                jt_d = f_jt.result()
                aging = f_ag.result()
                prod = f_pb.result()
                sa_s = f_ss.result()
                rev = f_rv.result()

            s_data = {(r['year'], r['month']): r['total'] or 0.0 for r in s_res['records']}
            cv = s_data.get((today_date.year, today_date.month), 0.0)
            pv = s_data.get((last_m_y, last_m_m), 0.0)
            
            if pv > 0:
                diff = float(cv) - float(pv)
                growth = (diff / float(pv)) * 100.0
                growth_abs = growth if growth >= 0 else -growth # type: ignore
                insights["sales"] = f"MTD Revenue is {'up' if diff >= 0 else 'down'} {growth_abs:.1f}% compared to same period last month."
            else:
                insights["sales"] = "MTD Revenue tracking properly."
            
            lc_val = (lc_res['records'][0].get('total', 0.0) or 0.0) / 1.2 if lc_res['records'] else 0.0
            total_collected = float(col.get("total", 0.0))
            if sum_m and sum_m.get("invoices"):
                insights["collections"] = f"MTD Collections: £{total_collected/1_000_000:.2f}M ({'up' if total_collected>=lc_val else 'down'} {abs(((total_collected-lc_val)/lc_val)*100 if lc_val>0 else 0):.1f}% vs £{lc_val/1_000_000:.2f}M last month)."
            else: 
                insights["collections"] = "Collection tracking active."

            t_sa = sum(int(r.get('cnt', 0)) for r in jt_d)
            f_sa_val = next((int(r.get('cnt', 0)) for r in jt_d if r.get('Job_Type__c') == 'Fixed Price'), 0)
            insights["job_type"] = f"Fixed-price contracts are driving {(f_sa_val/t_sa)*100:.1f}% of volume." if t_sa > 0 else "Job type split stabilizing."

            t_debt = aging.get("total", 0.0)
            under_30 = aging.get('buckets', {}).get('<30 Days', 0.0)
            insights["outstanding"] = f"Cash represents {(under_30/t_debt)*100:.1f}% of receivables." if t_debt > 0 else "Aging buckets monitored."
            
            tr_data = prod.get("trades", [])
            if tr_data: 
                top_trade = max(tr_data, key=lambda x: float(x.get('total', 0.0)))
                insights["sas"] = f"Performance strong in {top_trade.get('Trade_Group__c', 'Main')}."
            else: 
                insights["sas"] = "Performance trending positively."
            
            insights["collection_trend"] = "Collections trending higher than last month." if total_collected > lc_val else "Insights"
            insights["collection_total"] = f"We have made £{total_collected:,.2f} in collections so far this month."
            insights["sa_count"] = f"Completed {sa_s['month']['total']:,} service appointments so far."
            
            if sa_s['month'].get('trades'):
                top_trade = max(sa_s['month']['trades'], key=lambda x: x['value'])
                insights["top_trade_sa"] = f"{top_trade['name']} has the highest number of service appointments this month."
            else:
                insights["top_trade_sa"] = "Operational performance tracking properly."
            
            if rev["count"] > 0: 
                status = 'excellent' if rev['avg']>=4.4 else 'strong' if rev['avg']>=4.0 else 'good'
                insights["review_rating"] = f"We have {rev['count']} reviews this month. The average review rating is {rev['avg']}.\nStatus: {status.capitalize()}"
            else: 
                insights["review_rating"] = "Feedback being collected."
                
        except Exception as e:
            print(f"Insights Error: {e}")
            import traceback
            traceback.print_exc()
            insights = {"sales": "Steady.", "collections": "Normal.", "job_type": "Balanced.", "outstanding": "Managed.", "sas": "Positive."}
        return insights

sf_client = SalesforceClient()
