"""
WorldViewCache: Fetches raw Salesforce data once, caches in Pandas DataFrames for 15 minutes.
All filtering happens in data_processor.py (never in SOQL). Background refresh keeps data fresh
without blocking requests.
"""

import time
import threading
import traceback
from typing import Dict, Optional
from datetime import datetime

import pandas as pd
from simple_salesforce import Salesforce
from homeowner_mapping import postcode_to_region


TTL_SECONDS = 900  # 15 minutes


def _records_to_df(records) -> pd.DataFrame:
    """Convert simple-salesforce query records (list of dicts) to a flat DataFrame."""
    if not records:
        return pd.DataFrame()
    # Drop the SF metadata 'attributes' key
    flat = [{k: v for k, v in r.items() if k != 'attributes'} for r in records]
    return pd.DataFrame(flat)


def _flatten_relationships(df: pd.DataFrame, rel_field: str, prefix: str) -> pd.DataFrame:
    """
    Expand a nested relationship column (dict or None) into flat prefixed columns.
    e.g. rel_field='Account__r', prefix='account_' → account_Account_Type__c, ...
    """
    if rel_field not in df.columns:
        return df
    expanded = df[rel_field].apply(lambda x: {k: v for k, v in x.items() if k != 'attributes'} if isinstance(x, dict) else {})
    rel_df = pd.json_normalize(expanded).add_prefix(prefix)
    df = df.drop(columns=[rel_field]).reset_index(drop=True)
    rel_df = rel_df.reset_index(drop=True)
    return pd.concat([df, rel_df], axis=1)


def _add_year_month(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    """Parse a date string column and add integer year/month columns."""
    if date_col not in df.columns or df.empty:
        return df
    dt = pd.to_datetime(df[date_col].str[:10], errors='coerce')
    df = df.copy()
    df['year'] = dt.dt.year.astype('Int16')
    df['month'] = dt.dt.month.astype('Int8')
    return df


def _safe_postcode(val) -> str:
    """Return a string postcode, converting NaN/None/pd.NA to empty string."""
    try:
        if pd.isna(val):
            return ''
    except (TypeError, ValueError):
        pass
    return str(val) if val is not None else ''


def _apply_region(df: pd.DataFrame, postcode_col: str) -> pd.DataFrame:
    """Add a 'region' column by mapping postcodes via postcode_to_region()."""
    if postcode_col not in df.columns or df.empty:
        return df
    df = df.copy()
    df['region'] = df[postcode_col].apply(lambda pc: postcode_to_region(_safe_postcode(pc)))
    return df


class WorldViewCache:
    """
    Stale-while-revalidate cache for raw Salesforce data.

    Usage:
        cache = WorldViewCache(sf)
        cache.warm()  # call once on startup (blocks)
        wv = cache.get_world_view()  # fast — returns DataFrames dict
    """

    def __init__(self, sf: Salesforce):
        self._sf = sf
        self._lock = threading.Lock()
        self._data: Dict[str, pd.DataFrame] = {}
        self._loaded_at: float = 0.0
        self._is_refreshing: bool = False
        self._load_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def warm(self) -> None:
        """Synchronously load the cache. Call once at app startup."""
        print("[WorldViewCache] Warming cache...")
        self._load()

    def get_world_view(self) -> Dict[str, pd.DataFrame]:
        """
        Return cached DataFrames. Triggers background refresh when TTL expires.
        Raises RuntimeError if the cache is still warming on startup (never blocks the event loop).
        """
        now = time.time()
        with self._lock:
            age = now - self._loaded_at
            stale = age >= TTL_SECONDS
            has_data = bool(self._data)

        if not has_data:
            if self._is_refreshing or not self._load_lock.acquire(blocking=False):
                raise RuntimeError("Cache is still warming — please retry in a moment.")
            self._load_lock.release()
            self._load()
        elif stale and not self._is_refreshing:
            self._trigger_background_refresh()

        with self._lock:
            return dict(self._data)  # shallow copy — DataFrames are never mutated in place

    def get_status(self) -> dict:
        """Return cache metadata for debug endpoint."""
        with self._lock:
            age = time.time() - self._loaded_at
            row_counts = {k: len(v) for k, v in self._data.items()}
        return {
            "loaded_at": datetime.fromtimestamp(self._loaded_at).isoformat() if self._loaded_at else None,
            "age_seconds": round(age, 1),
            "ttl_seconds": TTL_SECONDS,
            "is_refreshing": self._is_refreshing,
            "row_counts": row_counts,
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _trigger_background_refresh(self) -> None:
        self._is_refreshing = True
        t = threading.Thread(target=self._load, daemon=True, name="wv-refresh")
        t.start()

    def _load(self) -> None:
        """Execute 5 SOQL queries, enrich, and atomically replace _data."""
        if not self._load_lock.acquire(blocking=False):
            # Already loading, just wait or return
            with self._load_lock:
                return

        try:
            print("[WorldViewCache] Loading raw data from Salesforce...")
            t0 = time.time()

            invoices = self._fetch_invoices()
            credits = self._fetch_credits()
            payments = self._fetch_payments()
            sas = self._fetch_service_appointments()
            outstanding = self._fetch_outstanding_invoices()

            elapsed = round(time.time() - t0, 1)
            rows = {k: len(v) for k, v in [
                ('invoices', invoices), ('credits', credits),
                ('payments', payments), ('sas', sas), ('outstanding', outstanding)
            ]}
            print(f"[WorldViewCache] Loaded in {elapsed}s — rows: {rows}")

            with self._lock:
                self._data = {
                    'invoices': invoices,
                    'credits': credits,
                    'payments': payments,
                    'sas': sas,
                    'outstanding': outstanding,
                }
                self._loaded_at = time.time()
        except Exception:
            print("[WorldViewCache] Load failed:")
            traceback.print_exc()
        finally:
            self._is_refreshing = False
            self._load_lock.release()

    # ------------------------------------------------------------------
    # SOQL fetch methods
    # ------------------------------------------------------------------

    def _fetch_invoices(self) -> pd.DataFrame:
        query = """
            SELECT Id, Name, Date__c, Charge_Net__c, Sector_Type__c,
                   Site_Postal_Code__c, Balance_Outstanding__c, Sum_of_Payments__c,
                   Interest_Fee_Owed__c, Interest_Fee_Received__c,
                   Job__c, Type__c, Job_Trade__c,
                   Account__r.Account_Type__c, Account__r.DRC_Applies__c
            FROM Customer_Invoice__c
            WHERE (Date__c = LAST_N_MONTHS:13 OR Date__c = THIS_MONTH)
            AND Chumley_Test_Record__c = False
            AND Account__r.Account_Type__c NOT IN ('Key Account', 'Key Accounts')
            AND (NOT Sector_Type__c LIKE '%Insurance%')
        """
        records = self._sf.query_all(query).get('records', [])
        df = _records_to_df(records)
        if df.empty:
            return df
        df = _flatten_relationships(df, 'Account__r', 'account_')
        # Rename for convenience
        df = df.rename(columns={
            'account_Account_Type__c': 'account_type',
            'account_DRC_Applies__c': 'drc_applies',
        })
        # Coerce numeric
        for col in ['Charge_Net__c', 'Balance_Outstanding__c', 'Sum_of_Payments__c',
                    'Interest_Fee_Owed__c', 'Interest_Fee_Received__c']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        df = _add_year_month(df, 'Date__c')
        df = _apply_region(df, 'Site_Postal_Code__c')
        return df

    def _fetch_credits(self) -> pd.DataFrame:
        query = """
            SELECT Id, Name, Date__c, Charge_Net__c,
                   Customer_Invoice__r.Name,
                   Customer_Invoice__r.Date__c,
                   Customer_Invoice__r.Sector_Type__c,
                   Customer_Invoice__r.Site_Postal_Code__c,
                   Customer_Invoice__r.Type__c,
                   Customer_Invoice__r.Job_Trade__c,
                   Customer_Invoice__r.Account__r.Account_Type__c
            FROM Customer_Credit_Note__c
            WHERE (Date__c = LAST_N_MONTHS:13 OR Date__c = THIS_MONTH)
            AND Customer_Invoice__r.Account__r.Account_Type__c NOT IN ('Key Account', 'Key Accounts')
            AND (NOT Customer_Invoice__r.Sector_Type__c LIKE '%Insurance%')
        """
        records = self._sf.query_all(query).get('records', [])
        df = _records_to_df(records)
        if df.empty:
            return df
        # Use json_normalize to handle double-nesting (Customer_Invoice__r.Account__r)
        if 'Customer_Invoice__r' in df.columns:
            inv_expanded = df['Customer_Invoice__r'].apply(
                lambda x: {k: v for k, v in x.items() if k != 'attributes'} if isinstance(x, dict) else {}
            )
            inv_df = pd.json_normalize(inv_expanded)
            inv_df = inv_df[[c for c in inv_df.columns if 'attributes' not in c]]
            inv_df.columns = ['inv_' + c for c in inv_df.columns]
            df = df.drop(columns=['Customer_Invoice__r']).reset_index(drop=True)
            df = pd.concat([df.reset_index(drop=True), inv_df.reset_index(drop=True)], axis=1)

        col_map = {}
        for c in df.columns:
            if c == 'inv_Name': col_map[c] = 'invoice_name'
            elif c == 'inv_Date__c': col_map[c] = 'invoice_date'
            elif c == 'inv_Sector_Type__c': col_map[c] = 'invoice_sector'
            elif c == 'inv_Site_Postal_Code__c': col_map[c] = 'invoice_postcode'
            elif c == 'inv_Type__c': col_map[c] = 'invoice_type'
            elif c == 'inv_Job_Trade__c': col_map[c] = 'invoice_trade_group'
            elif 'Account_Type' in c: col_map[c] = 'invoice_account_type'
        df = df.rename(columns=col_map)
        df['Charge_Net__c'] = pd.to_numeric(df['Charge_Net__c'], errors='coerce').fillna(0.0)
        df = _add_year_month(df, 'Date__c')
        # region from the invoice's postcode
        if 'invoice_postcode' in df.columns:
            df['region'] = df['invoice_postcode'].apply(lambda pc: postcode_to_region(_safe_postcode(pc)))
        return df

    def _fetch_payments(self) -> pd.DataFrame:
        query = """
            SELECT Id, asp04__Amount__c, asp04__Payment_Date__c,
                   asp04__Payment_Stage__c, asp04__Payment_Route_Selected__c,
                   Customer_Invoice__r.Name,
                   Customer_Invoice__r.Date__c,
                   Customer_Invoice__r.Sector_Type__c,
                   Customer_Invoice__r.Job_Trade__c,
                   Customer_Invoice__r.Site_Postal_Code__c,
                   Customer_Invoice__r.Account__r.Account_Type__c
            FROM asp04__Payment__c
            WHERE (asp04__Payment_Date__c = LAST_N_MONTHS:13
                   OR asp04__Payment_Date__c = THIS_MONTH)
            AND Customer_Invoice__r.Account__r.Account_Type__c NOT IN ('Key Account', 'Key Accounts')
            AND (NOT Customer_Invoice__r.Sector_Type__c LIKE '%Insurance%')
        """
        records = self._sf.query_all(query).get('records', [])
        df = _records_to_df(records)
        if df.empty:
            return df
        # Flatten nested Customer_Invoice__r which may itself contain Account__r
        # Handle double-nesting: Customer_Invoice__r.Account__r
        if 'Customer_Invoice__r' in df.columns:
            inv_expanded = df['Customer_Invoice__r'].apply(
                lambda x: {k: v for k, v in x.items() if k != 'attributes'} if isinstance(x, dict) else {}
            )
            inv_df = pd.json_normalize(inv_expanded)
            # Drop attributes cols
            inv_df = inv_df[[c for c in inv_df.columns if 'attributes' not in c]]
            inv_df.columns = ['inv_' + c for c in inv_df.columns]
            df = df.drop(columns=['Customer_Invoice__r']).reset_index(drop=True)
            inv_df = inv_df.reset_index(drop=True)
            df = pd.concat([df, inv_df], axis=1)

        # Rename
        col_map = {}
        for c in df.columns:
            if c == 'inv_Name': col_map[c] = 'invoice_name'
            elif c == 'inv_Date__c': col_map[c] = 'invoice_date'
            elif c == 'inv_Sector_Type__c': col_map[c] = 'invoice_sector'
            elif c == 'inv_Site_Postal_Code__c': col_map[c] = 'invoice_postcode'
            elif c == 'inv_Job_Trade__c': col_map[c] = 'invoice_trade_group'
            elif 'Account_Type' in c: col_map[c] = 'invoice_account_type'
        df = df.rename(columns=col_map)

        df['asp04__Amount__c'] = pd.to_numeric(df['asp04__Amount__c'], errors='coerce').fillna(0.0)
        df = _add_year_month(df, 'asp04__Payment_Date__c')
        if 'invoice_postcode' in df.columns:
            df['region'] = df['invoice_postcode'].apply(lambda pc: postcode_to_region(_safe_postcode(pc)))
        return df

    def _fetch_service_appointments(self) -> pd.DataFrame:
        query = """
            SELECT Id, Job_Number__c, Job_Type__c, ActualStartTime, PostalCode,
                   Review_Star_Rating__c, Job__c,
                   Job__r.Job_Type_Trade__c,
                   Job__r.Sector_Type__c,
                   Trade_Group__c,
                   Job__r.Account__r.Account_Type__c,
                   Job__r.Account__r.CreatedDate,
                   Job__r.Account__r.Name
            FROM ServiceAppointment
            WHERE (ActualStartTime = LAST_N_MONTHS:13 OR ActualStartTime = THIS_MONTH)
            AND Chumley_Test_Account__c = false
            AND Job__r.Account__r.Account_Type__c NOT IN ('Key Account', 'Key Accounts')
            AND (NOT Job__r.Sector_Type__c LIKE '%Insurance%')
        """
        records = self._sf.query_all(query).get('records', [])
        df = _records_to_df(records)
        if df.empty:
            return df
        # Flatten Job__r (which contains nested Account__r)
        if 'Job__r' in df.columns:
            job_expanded = df['Job__r'].apply(
                lambda x: {k: v for k, v in x.items() if k != 'attributes'} if isinstance(x, dict) else {}
            )
            job_df = pd.json_normalize(job_expanded)
            job_df = job_df[[c for c in job_df.columns if 'attributes' not in c]]
            job_df.columns = ['job_' + c for c in job_df.columns]
            df = df.drop(columns=['Job__r']).reset_index(drop=True)
            job_df = job_df.reset_index(drop=True)
            df = pd.concat([df, job_df], axis=1)

        col_map = {}
        for c in df.columns:
            if c == 'job_Job_Type_Trade__c': col_map[c] = 'job_type_trade'
            elif 'Account_Type' in c and 'job_' in c: col_map[c] = 'account_type'
            elif 'CreatedDate' in c and 'job_' in c: col_map[c] = 'account_created_date'
            elif 'Account__r.Name' in c or (c.startswith('job_') and c.endswith('Name')): col_map[c] = 'account_name'
        df = df.rename(columns=col_map)

        df['Review_Star_Rating__c'] = pd.to_numeric(df.get('Review_Star_Rating__c'), errors='coerce')
        df = _add_year_month(df, 'ActualStartTime')
        df = _apply_region(df, 'PostalCode')
        return df

    def _fetch_outstanding_invoices(self) -> pd.DataFrame:
        """All open receivables — no date window filter."""
        query = """
            SELECT Name, Date__c, Charge_Net__c, Sum_of_Payments__c,
                   Interest_Fee_Owed__c, Interest_Fee_Received__c,
                   Account__r.Account_Type__c, Account__r.DRC_Applies__c,
                   Balance_Outstanding__c, Sector_Type__c, Site_Postal_Code__c,
                   Job_Trade__c
            FROM Customer_Invoice__c
            WHERE Chumley_Test_Record__c = False
            AND Date__c != NULL
            AND (Balance_Outstanding__c > 0 OR Interest_Fee_Owed__c > 0)
        """
        records = self._sf.query_all(query).get('records', [])
        df = _records_to_df(records)
        if df.empty:
            return df
        df = _flatten_relationships(df, 'Account__r', 'account_')
        df = df.rename(columns={
            'account_Account_Type__c': 'account_type',
            'account_DRC_Applies__c': 'drc_applies',
        })
        for col in ['Charge_Net__c', 'Sum_of_Payments__c', 'Interest_Fee_Owed__c',
                    'Interest_Fee_Received__c', 'Balance_Outstanding__c']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        df = _apply_region(df, 'Site_Postal_Code__c')
        return df
