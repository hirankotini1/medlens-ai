"""
Daily Operations Report & Export Generator
"""
import io 
import csv 
from typing import Dict ,Any ,List 
from datetime import datetime 
from disease_prediction .hospital_operations .models import UnifiedOperationsOverview 


class DailyOperationsReportGenerator :
    """
    Generates structured, print-ready, and exportable operational daily briefings
    from the single reconciled hospital operations data model.
    """

    @staticmethod 
    def generate_html_report (overview :UnifiedOperationsOverview )->str :
        """
        Builds a styled, printable HTML briefing document.
        """
        now_str =datetime .now ().strftime ("%d-%b-%Y %H:%M")

        wards_html ="".join ([
        f"""
            <tr>
                <td style="padding: 8px 12px; border-bottom: 1px solid #e2e8f0; font-weight: 600;">{w ['ward_name']}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #e2e8f0; text-align: center;">{w ['total_beds']}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #e2e8f0; text-align: center; color: #b91c1c; font-weight: 700;">{w ['occupied_beds']}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #e2e8f0; text-align: center; color: #15803d; font-weight: 700;">{w ['available_beds']}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #e2e8f0; text-align: center;">
                    <span style="display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 12px; font-weight: 700; background: {'#fee2e2; color: #991b1b;'if w ['status']=='Critical'else ('#fef3c7; color: #92400e;'if w ['status']=='Warning'else '#dcfce7; color: #166534;')};">
                        {w ['occupancy_percentage']}% ({w ['status']})
                    </span>
                </td>
            </tr>
            """
        for w in overview .bed_capacity .ward_breakdown 
        ])

        alerts_html ="".join ([
        f"""
            <div style="padding: 10px 14px; margin-bottom: 8px; border-radius: 6px; background: {'#fef2f2; border-left: 4px solid #ef4444;'if a .severity =='Critical'else ('#fffbeb; border-left: 4px solid #f59e0b;'if a .severity =='Warning'else '#f0f9ff; border-left: 4px solid #0284c7;')};">
                <div style="font-weight: 700; font-size: 13px; color: #0f172a;">{a .title }</div>
                <div style="font-size: 12px; color: #475569; margin-top: 2px;">{a .message }</div>
                <div style="font-size: 11px; color: #64748b; margin-top: 4px;"><strong>Action:</strong> {a .recommended_action }</div>
            </div>
            """
        for a in overview .top_alerts [:5 ]
        ])

        html =f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>MEDLENS Hospital Daily Operations Briefing — {now_str }</title>
    <style>
        body {{ font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif; color: #0f172a; margin: 0; padding: 24px; background: #ffffff; line-height: 1.5; }}
        .header-box {{ border-bottom: 2px solid #0284c7; padding-bottom: 14px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: flex-end; }}
        .header-title {{ font-size: 22px; font-weight: 800; color: #00397e; margin: 0; }}
        .header-sub {{ font-size: 12px; color: #64748b; margin: 2px 0 0 0; }}
        .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 24px; }}
        .kpi-card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; text-align: center; }}
        .kpi-val {{ font-size: 24px; font-weight: 800; color: #0284c7; margin: 4px 0; }}
        .kpi-lbl {{ font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; }}
        .section-title {{ font-size: 15px; font-weight: 700; color: #1e293b; margin: 20px 0 10px 0; border-bottom: 1px solid #cbd5e1; padding-bottom: 4px; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
        th {{ background: #f1f5f9; padding: 8px 12px; text-align: left; font-size: 11px; font-weight: 700; color: #475569; text-transform: uppercase; }}
        .footer {{ margin-top: 30px; border-top: 1px solid #e2e8f0; padding-top: 10px; font-size: 11px; color: #94a3b8; text-align: center; }}
        @media print {{
            body {{ padding: 0; }}
            .no-print {{ display: none; }}
        }}
    </style>
</head>
<body>
    <div class="header-box">
        <div>
            <h1 class="header-title">MEDLENS AI &bull; Hospital Operations Executive Briefing</h1>
            <p class="header-sub">Medicover Hospital Multi-Source Reconciled Operations Report</p>
        </div>
        <div style="text-align: right; font-size: 12px; color: #475569;">
            <div><strong>Report Date:</strong> {now_str }</div>
            <div><strong>Data Quality Score:</strong> <span style="color: #15803d; font-weight: 700;">{overview .data_quality_score }%</span></div>
        </div>
    </div>

    <!-- 4 Core Questions KPI Grid -->
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-lbl">Active Inpatients</div>
            <div class="kpi-val" style="color: #0284c7;">{overview .active_inpatient_census }</div>
            <div style="font-size: 11px; color: #64748b;">Admissions ledger</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-lbl">Bed Occupancy</div>
            <div class="kpi-val" style="color: #ea580c;">{overview .bed_occupancy_percentage }%</div>
            <div style="font-size: 11px; color: #64748b;">{overview .total_beds_occupied } of {overview .total_hospital_capacity } beds</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-lbl">Lab Turnaround (Avg)</div>
            <div class="kpi-val" style="color: #4f46e5;">{overview .lab_turnaround_avg_hours } hrs</div>
            <div style="font-size: 11px; color: #64748b;">STAT: {overview .stat_turnaround_avg_hours } hrs</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-lbl">Reconciliation Status</div>
            <div class="kpi-val" style="color: #16a34a;">{overview .data_quality .resolved_conflicts_count } / {overview .total_conflicts_count }</div>
            <div style="font-size: 11px; color: #64748b;">Conflicts resolved</div>
        </div>
    </div>

    <!-- Bed Capacity Table -->
    <div class="section-title">Ward-by-Ward Capacity & Occupancy Status</div>
    <table>
        <thead>
            <tr>
                <th>Ward Name</th>
                <th style="text-align: center;">Total Capacity</th>
                <th style="text-align: center;">Occupied</th>
                <th style="text-align: center;">Available</th>
                <th style="text-align: center;">Utilization %</th>
            </tr>
        </thead>
        <tbody>
            {wards_html }
        </tbody>
    </table>

    <!-- Laboratory Turnaround Summary -->
    <div class="section-title">Laboratory Diagnostic Performance & Delays</div>
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; font-size: 13px;">
        <div style="background: #f8fafc; padding: 12px; border-radius: 6px; border: 1px solid #e2e8f0;">
            <div style="font-weight: 700; margin-bottom: 6px;">Priority Tier Turnaround Times:</div>
            <div>&bull; <strong>STAT Emergency:</strong> {overview .lab_performance .priority_performance .get ('STAT',{}).get ('avg_turnaround_hours',0 )} hrs ({overview .lab_performance .priority_performance .get ('STAT',{}).get ('delayed_count',0 )} delayed)</div>
            <div>&bull; <strong>URGENT:</strong> {overview .lab_performance .priority_performance .get ('URGENT',{}).get ('avg_turnaround_hours',0 )} hrs ({overview .lab_performance .priority_performance .get ('URGENT',{}).get ('delayed_count',0 )} delayed)</div>
            <div>&bull; <strong>ROUTINE:</strong> {overview .lab_performance .priority_performance .get ('ROUTINE',{}).get ('avg_turnaround_hours',0 )} hrs</div>
        </div>
        <div style="background: #f8fafc; padding: 12px; border-radius: 6px; border: 1px solid #e2e8f0;">
            <div style="font-weight: 700; margin-bottom: 6px;">Workload & Queue Status:</div>
            <div>&bull; <strong>Total Orders:</strong> {overview .lab_performance .total_tests_ordered } ({overview .lab_performance .total_tests_completed } completed)</div>
            <div>&bull; <strong>Active Pending Queue:</strong> {overview .lab_performance .total_tests_pending } orders</div>
            <div>&bull; <strong>Pre-Analytical Collection Lag:</strong> {overview .lab_performance .avg_order_to_collect_minutes } mins</div>
        </div>
    </div>

    <!-- Operational Alerts -->
    <div class="section-title">Critical Operational Alerts & Recommendations</div>
    {alerts_html }

    <div class="footer">
        Generated autonomously by MEDLENS Hospital Operations Intelligence &bull; Multi-Source Deterministic Reconciliation Engine &bull; Confidential &bull; For Hospital Leadership Use Only
    </div>
</body>
</html>
        """
        return html 

    @staticmethod 
    def generate_csv_summary (overview :UnifiedOperationsOverview )->str :
        """
        Generates CSV export of key reconciled operational data.
        """
        output =io .StringIO ()
        writer =csv .writer (output )

        writer .writerow (["MEDLENS Hospital Operations Daily Export"])
        writer .writerow (["Generated At",datetime .now ().strftime ("%Y-%m-%d %H:%M:%S")])
        writer .writerow ([])
        writer .writerow (["METRIC","VALUE","NOTES"])
        writer .writerow (["Active Inpatient Census",overview .active_inpatient_census ,"Admitted patients without discharge timestamp"])
        writer .writerow (["Total Hospital Capacity",overview .total_hospital_capacity ,"Total beds across 5 wards"])
        writer .writerow (["Total Occupied Beds",overview .total_beds_occupied ,"Reconciled occupied beds"])
        writer .writerow (["Total Available Beds",overview .total_beds_available ,"Reconciled available beds"])
        writer .writerow (["Bed Occupancy %",f"{overview .bed_occupancy_percentage }%",overview .bed_capacity .overall_status ])
        writer .writerow (["Average Lab Turnaround",f"{overview .lab_turnaround_avg_hours } hrs","Overall order-to-result"])
        writer .writerow (["STAT Lab Turnaround",f"{overview .stat_turnaround_avg_hours } hrs","Emergency orders"])
        writer .writerow (["Pending Lab Queue",overview .lab_pending_tests_count ,"Orders awaiting completion"])
        writer .writerow (["Data Quality Score",f"{overview .data_quality_score }%",overview .data_quality .rating ])
        writer .writerow ([])
        writer .writerow (["WARD CAPACITY BREAKDOWN"])
        writer .writerow (["Ward Name","Total Beds","Occupied","Available","Occupancy %","Status","Remarks"])
        for w in overview .bed_capacity .ward_breakdown :
            writer .writerow ([w ["ward_name"],w ["total_beds"],w ["occupied_beds"],w ["available_beds"],f"{w ['occupancy_percentage']}%",w ["status"],w .get ("remarks","")])

        return output .getvalue ()
