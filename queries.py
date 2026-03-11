
# ============================================================
# SOQL Query Filters
# ============================================================

KEY_ACCOUNTS_FILTER_JOB = (
    "AND Sector_Type__c != 'Key accounts' AND Account_Type__c != 'Key accounts'"
)

KEY_ACCOUNTS_FILTER_SA = (
    "AND Job__r.Sector_Type__c != 'Key accounts' AND Job__r.Account_Type__c != 'Key accounts'"
)

# ============================================================
# Query String Generator Functions
# ============================================================

def get_service_resources_query() -> str:
    return """
        SELECT Id, Name, RelatedRecord.Email, Email__c, Trade_Lookup__c
        FROM ServiceResource
        WHERE Trade_Lookup__c != NULL 
        AND IsActive = true
        AND Is_User_Active__c = true
        AND Account.Chumley_Test_Record__c = false
        AND FSM__c = false
        AND RelatedRecord.Profile_Name__c = 'Engineer Partner Community'
    """

def get_ops_count_query(trades_str: str) -> str:
    return f"""
        SELECT COUNT(Id) cnt
        FROM ServiceResource 
        WHERE Is_User_Active__c = true 
        AND IsActive = true 
        AND Account.Chumley_Test_Record__c = false 
        AND FSM__c = false
        AND RelatedRecord.Profile_Name__c = 'Engineer Partner Community'
        AND Trade_Lookup__c IN ({trades_str})
    """

def get_total_ops_count_query() -> str:
    return """
        SELECT COUNT(Id) cnt
        FROM ServiceResource 
        WHERE Is_User_Active__c = true 
        AND IsActive = true 
        AND Account.Chumley_Test_Record__c = false 
        AND FSM__c = false
        AND RelatedRecord.Profile_Name__c = 'Engineer Partner Community'
        AND Trade_Lookup__c NOT IN ('Key', 'Utilities', 'PM')
        AND Trade_Lookup__c != NULL
    """

def get_cases_count_query(trades_str: str, start_iso: str, end_iso: str) -> str:
    return f"""
        SELECT COUNT(Id) cnt
        FROM Case
        WHERE Service_Resource__r.Name != NULL
        AND Service_Resource__r.Trade_Lookup__c IN ({trades_str})
        AND CreatedDate >= {start_iso} AND CreatedDate < {end_iso}
        AND Case_Type__c IN ('Issue with work carried out', 'Engineer Related', 'Documentation')
    """

def get_engineer_satisfaction_query(trades_str: str, start_iso: str, end_iso: str) -> str:
    return f"""
        SELECT Total_Score__c, Service_Resource__r.Name, Service_Resource__r.Trade_Lookup__c
        FROM Survey_Form__c
        WHERE Service_Resource__r.Trade_Lookup__c IN ({trades_str})
        AND CreatedDate >= {start_iso} AND CreatedDate < {end_iso}
        AND Total_Score__c != NULL
    """

def get_total_invoice_sales_query(start_date: str, end_date: str) -> str:
    return f"""
        SELECT SUM(Charge_Net__c) total_sales
        FROM Customer_Invoice__c
        WHERE Sector_Type__c != 'Key accounts'
        AND Account_Type__c != 'Key accounts'
        AND Chumley_Test_Record__c = false
        AND Date__c >= {start_date}
        AND Date__c <= {end_date}
    """

def get_filtered_invoice_sales_query(trade_list: str, start_date: str, end_date: str) -> str:
    return f"""
        SELECT SUM(Charge_Net__c) total_sales
        FROM Customer_Invoice__c
        WHERE Sector_Type__c != 'Key accounts'   
        AND Account_Type__c != 'Key Account'
        AND Chumley_Test_Record__c = false
        AND Job_Trade__c IN ({trade_list})
        AND Date__c >= {start_date}
        AND Date__c <= {end_date}
    """

def get_job_history_closed_query(start_iso: str, end_iso: str) -> str:
    return f"""
        SELECT Id, ParentId, CreatedDate, Field, OldValue, NewValue
        FROM Job__History WHERE Field = 'Status__c'
        AND CreatedDate >= {start_iso} AND CreatedDate < {end_iso}
    """

def get_jobs_by_ids_query(id_str: str) -> str:
    return f"""
        SELECT Id, Name, Job_Type_Trade__c, Type__c, Status__c, Charge_Policy__c,
               Customer_Facing_Description__c, Raised_from_Job__c, CreatedDate, Job_Duration__c,
               Sector_Type__c, Account_Type__c
        FROM Job__c 
        WHERE Id IN ({id_str})
        AND Is_Test_Job__c = false
        {KEY_ACCOUNTS_FILTER_JOB}
    """

def get_jobs_created_between_query(trades_str: str, start_iso: str, end_iso: str) -> str:
    return f"""
        SELECT Id, Name, CreatedDate, Job_Type_Trade__c, Charge_Policy__c,
               Status__c, Raised_from_Job__c, Type__c, Job_Duration__c,
               Created_By_Profile_Name__c, Charge_Net__c, Site_Id__c, Is_Test_Job__c,
               Sector_Type__c, Account_Type__c
        FROM Job__c 
        WHERE Job_Type_Trade__c IN ({trades_str})
        AND CreatedDate >= {start_iso} AND CreatedDate < {end_iso}
        AND Is_Test_Job__c = false
        {KEY_ACCOUNTS_FILTER_JOB}
    """

def get_service_appointments_query(id_str: str) -> str:
    return f"""
        SELECT
            Id,
            Job__c,
            Post_Visit_Report_Check__c,
            Job__r.Final_WO_Is_the_Customer_Satisfied__c,
            Status,
            CreatedDate,
            ActualStartTime,
            ArrivalWindowStartTime,
            Review_Star_Rating__c,
            Signed_SR__c,
            Job__r.Sector_Type__c,
            Job__r.Account_Type__c
        FROM ServiceAppointment
        WHERE Job__c IN ({id_str})
        AND Chumley_Test_Account__c = false
        {KEY_ACCOUNTS_FILTER_SA}
    """

def get_service_appointments_month_query(trades_str: str, start_iso: str, end_iso: str) -> str:
    return f"""
        SELECT Id, Job__c, Status, CreatedDate, ActualStartTime, Job__r.Job_Type_Trade__c,
               Job__r.Sector_Type__c, Job__r.Account_Type__c
        FROM ServiceAppointment 
        WHERE ActualStartTime >= {start_iso} AND ActualStartTime < {end_iso}
        AND Job__r.Job_Type_Trade__c IN ({trades_str})
        {KEY_ACCOUNTS_FILTER_SA}
    """

def get_service_appointments_by_actual_start_query(trades_str: str, start_iso: str, end_iso: str) -> str:
    return f"""
        SELECT Id, AppointmentNumber, Job__c, Job__r.Name, Status, CreatedDate, ActualStartTime, ArrivalWindowStartTime,
               Review_Star_Rating__c, Signed_SR__c,
               Job__r.Job_Type_Trade__c, Job__r.Sector_Type__c, Job__r.Account_Type__c
        FROM ServiceAppointment 
        WHERE ActualStartTime >= {start_iso} AND ActualStartTime < {end_iso}
        AND Job__r.Job_Type_Trade__c IN ({trades_str})
        {KEY_ACCOUNTS_FILTER_SA}
    """

def get_workorders_month_query(trades_str: str, start_iso: str, end_iso: str) -> str:
    return f"""
        SELECT Id, CreatedDate, CCT_Charge_NET__c, WO_Status__c,
               Created_by_Profile_Name__c, Trade__c, Record_Type_Name__c, Status
        FROM WorkOrder WHERE CreatedDate >= {start_iso} AND CreatedDate < {end_iso}
        AND Trade__c IN ({trades_str})
    """

def get_vcr_forms_query(start_iso: str, end_iso: str) -> str:
    return f"""
        SELECT Id, Current_Engineer_Assigned_to_Vehicle__c, CreatedDate
        FROM Vehicle_Condition_Form__c
        WHERE CreatedDate >= {start_iso}
        AND CreatedDate < {end_iso}
    """

def get_jobs_created_and_closed_count_query(trades_str: str, start_iso: str, end_iso: str) -> str:
    return f"""
        SELECT COUNT(Id)
        FROM Job__c
        WHERE Job_Type_Trade__c IN ({trades_str})
        AND CreatedDate >= {start_iso}
        AND CreatedDate < {end_iso}
        AND Status__c = 'Closed'
        AND Is_Test_Job__c = false
        {KEY_ACCOUNTS_FILTER_JOB}
    """

def get_sa_job_types_query() -> str:
    return """
        SELECT Job_Type__c, COUNT(Id) cnt
        FROM ServiceAppointment
        WHERE ActualStartTime = THIS_MONTH
        GROUP BY Job_Type__c
    """
