# 📊 TGM Bonus Dashboard - KPI Diary

This document provides a detailed breakdown of all Key Performance Indicators (KPIs) displayed on the TGM Bonus Dashboard. It explains the purpose, calculation logic, and target context for each metric.

---

## 🔝 Summary Metrics
These high-level metrics determine the overall performance band and bonus eligibility.

| Metric | Description | Calculation |
| :--- | :--- | :--- |
| **Overall Score** | The weighted average of all category scores. | `Average of Category Scores` |
| **Bonus Multiplier** | Determins the bonus band (Below, Bronze, Silver, Gold). | Based on `Overall Score` thresholds. |

---

## 📈 Conversion
Focuses on the efficiency of turning leads and estimates into closed business.

### Estimate Production / Reactive Leads %
- **Purpose**: Measures the rate at which reactive leads result in an estimate.
- **Calculation**: `(Total Estimates Produced / Total Reactive Leads) * 100`

### Estimate Conversion %
- **Purpose**: Measures the percentage of estimates that are successful (Converted or Closed).
- **Calculation**: `(Converted + Closed Estimates / Total Estimates Produced) * 100`

### FOC Conversion Rate %
- **Purpose**: Focuses on professional conversion by excluding "Free of Charge" (FOC) leads.
- **Calculation**: `(Converted Jobs / (Total Estimates - FOC Estimates)) * 100`

### Average Converted Estimate Value (£)
- **Purpose**: Measures the average GBP value of estimates that were successfully converted.
- **Calculation**: `Sum(Charge Net of Converted Jobs) / Count(Converted Jobs)`

---

## ⚙️ Procedural
Ensures that operational standards and reporting requirements are met.

### TQR Ratio %
- **Purpose**: Tracks the percentage of jobs where a Technical Quality Report (TQR) was completed.
- **Calculation**: `(Total TQR Reports / Total Closed Jobs) * 100`

### TQR (Not Satisfied) Ratio %
- **Purpose**: Measures negative customer feedback within TQR reports.
- **Calculation**: `(TQR reports marked 'No' for satisfaction / Total TQR Reports) * 100`

### Unclosed SA %
- **Purpose**: Monitors Service Appointments (SA) that haven't been finalized.
- **Calculation**: `(SAs not 'Visit Complete' or 'Cancelled' / Total SAs) * 100`

### Reactive 6+ hours %
- **Purpose**: Tracks long-duration reactive jobs which may indicate complexity or inefficiency.
- **Calculation**: `(Reactive jobs taking > 6 hours / Total Reactive Jobs) * 100`

---

## 😊 Satisfaction
Benchmarks quality of service and brand reputation.

### Average Review Rating
- **Purpose**: The average star rating from customer reviews.
- **Calculation**: `Average(Review_Star_Rating__c)`

### Review Ratio %
- **Purpose**: The percentage of completed visits that resulted in a customer review.
- **Calculation**: `(Count of Reviews / SAs Attended) * 100`

### Engineer Satisfaction %
- **Purpose**: Internal metric measuring engineer engagement and satisfaction.
- **Calculation**: `Average score from Survey Forms`

### Cases %
- **Purpose**: Customer service cases raised against the trade group.
- **Calculation**: `(Total Cases / Total Jobs from Previous Month) * 100`

### Engineer Retention %
- **Purpose**: Percentage of engineers retained over the period.
- **Calculation**: `(Current Engineers / Engineers at Start of Period) * 100` *(Currently set to 80% placeholder)*

---

## 🚚 Vehicular
Focuses on fleet safety and maintenance.

### Average Driving Score
- **Purpose**: Fleet safety metric based on Webfleet OptiDrive data.
- **Calculation**: `Average OptiDrive Score * 10`

### Drivers with <7 %
- **Purpose**: Identifies high-risk drivers with low safety scores.
- **Calculation**: `(Drivers with score < 7.0 / Total Drivers) * 100`

### VCR Update %
- **Purpose**: Compliance with weekly Vehicle Condition Reports (VCR).
- **Calculation**: `(Total VCR Forms / (Ops Count * 4 weeks)) * 100`

---

## ⚡ Productivity
Measures the volume and financial throughput of the trade group.

### Ops Count %
- **Purpose**: Compares actual active engineer count against the monthly target.
- **Calculation**: `(Actual Active Engineers / Target Engineers) * 100`

### Sales Target Achievement %
- **Purpose**: Measures actual invoiced sales against the monthly GBP target.
- **Calculation**: `(Total Invoiced Sales / Target Sales) * 100`

### Monthly Working Time (hrs)
- **Purpose**: Total productive hours worked by the group.
- **Calculation**: `Sum of Job Durations` *(Currently set to 200.0 placeholder)*

### Callback Jobs %
- **Purpose**: Measures rework or returned visits.
- **Calculation**: `(Jobs marked as Callbacks / Total Jobs) * 100`

### SA Attended
- **Purpose**: Absolute count of Service Appointments successfully attended.
- **Calculation**: `Count of SAs with 'Visit Complete' status`

### Average Site Value (£)
- **Purpose**: Average financial value of all work performed at a site.
- **Calculation**: `Average(Charge Net) across all jobs`

### Late to Site %
- **Purpose**: Punctuality metric based on arrival windows.
- **Calculation**: `(SAs where Actual Start > Arrival Window Start + 30m / Total SAs) * 100`

### Absence %
- **Purpose**: Group-wide absence rate.
- **Calculation**: `(Days Absent / Total Scheduled Days) * 100` *(Currently set to 10.0 placeholder)*

---
> [!NOTE]
> All targets and thresholds are defined in `thresholds.json` and are specific to each Trade Group.
