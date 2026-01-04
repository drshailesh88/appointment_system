"""
Reports & Exports Service.

Phase 8: Professional PDF and Excel report generation.
Leverages analytics service for data and supports branded templates.

Libraries:
- fpdf2: PDF generation
- pandas + openpyxl: Excel export
- xlsxwriter: Advanced Excel formatting
"""

import io
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Optional, BinaryIO
from uuid import UUID

import pandas as pd
from fpdf import FPDF
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.chart import BarChart, Reference, PieChart
from openpyxl.utils.dataframe import dataframe_to_rows
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinic import Clinic
from app.models.appointment import Appointment, AppointmentStatus
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.invoice import Invoice
from app.services.analytics import (
    AnalyticsService,
    AppointmentStats,
    RevenueStats,
    DoctorUtilization,
    DailyMetric,
    PatientDemographics,
)

logger = logging.getLogger(__name__)


@dataclass
class ReportConfig:
    """Configuration for report generation."""
    clinic_name: str
    clinic_address: str = ""
    clinic_phone: str = ""
    clinic_email: str = ""
    logo_path: Optional[Path] = None
    primary_color: tuple = (41, 128, 185)  # Blue
    secondary_color: tuple = (52, 73, 94)  # Dark gray


class PDFReport(FPDF):
    """Custom PDF class with branded header/footer."""

    def __init__(self, config: ReportConfig):
        super().__init__()
        self.config = config
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        """Add branded header to each page."""
        # Logo if available
        if self.config.logo_path and self.config.logo_path.exists():
            self.image(str(self.config.logo_path), 10, 8, 30)
            self.set_xy(45, 10)
        else:
            self.set_xy(10, 10)

        # Clinic name
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*self.config.primary_color)
        self.cell(0, 8, self.config.clinic_name, ln=True)

        # Clinic contact
        self.set_font("Helvetica", "", 9)
        self.set_text_color(100, 100, 100)
        if self.config.clinic_address:
            self.cell(0, 4, self.config.clinic_address, ln=True)
        if self.config.clinic_phone or self.config.clinic_email:
            contact = f"{self.config.clinic_phone} | {self.config.clinic_email}".strip(" |")
            self.cell(0, 4, contact, ln=True)

        # Line separator
        self.ln(2)
        self.set_draw_color(*self.config.primary_color)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(8)

    def footer(self):
        """Add footer with page number and timestamp."""
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")
        self.set_y(-15)
        self.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", align="R")

    def add_title(self, title: str, subtitle: str = ""):
        """Add report title."""
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(*self.config.secondary_color)
        self.cell(0, 10, title, ln=True, align="C")

        if subtitle:
            self.set_font("Helvetica", "", 11)
            self.set_text_color(100, 100, 100)
            self.cell(0, 6, subtitle, ln=True, align="C")
        self.ln(8)

    def add_section(self, title: str):
        """Add section header."""
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*self.config.primary_color)
        self.cell(0, 8, title, ln=True)
        self.ln(2)

    def add_metric_box(self, label: str, value: str, x: float, y: float, width: float = 45):
        """Add a styled metric box."""
        self.set_xy(x, y)

        # Box background
        self.set_fill_color(245, 247, 250)
        self.rect(x, y, width, 20, "F")

        # Value
        self.set_xy(x, y + 2)
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*self.config.primary_color)
        self.cell(width, 8, value, align="C")

        # Label
        self.set_xy(x, y + 11)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(100, 100, 100)
        self.cell(width, 6, label, align="C")

    def add_table(self, headers: list, rows: list, col_widths: Optional[list] = None):
        """Add a styled table."""
        if not col_widths:
            col_widths = [190 / len(headers)] * len(headers)

        # Header row
        self.set_font("Helvetica", "B", 10)
        self.set_fill_color(*self.config.primary_color)
        self.set_text_color(255, 255, 255)

        for i, header in enumerate(headers):
            self.cell(col_widths[i], 8, str(header), border=1, fill=True, align="C")
        self.ln()

        # Data rows
        self.set_font("Helvetica", "", 9)
        self.set_text_color(0, 0, 0)
        fill = False

        for row in rows:
            if fill:
                self.set_fill_color(245, 247, 250)
            else:
                self.set_fill_color(255, 255, 255)

            for i, cell in enumerate(row):
                self.cell(col_widths[i], 7, str(cell), border=1, fill=True, align="C")
            self.ln()
            fill = not fill


class ReportService:
    """
    Report generation service.

    Generates PDF and Excel reports from analytics data.
    Supports:
    - Daily summary reports
    - Monthly analytics reports
    - Revenue reports
    - Appointment reports
    - Doctor utilization reports
    - Patient demographics reports
    """

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db
        self.analytics = AnalyticsService(db)

    async def _get_clinic_config(self, clinic_id: UUID) -> ReportConfig:
        """Get clinic configuration for branding."""
        from sqlalchemy import select

        result = await self.db.execute(
            select(Clinic).where(Clinic.id == clinic_id)
        )
        clinic = result.scalar_one_or_none()

        if clinic:
            return ReportConfig(
                clinic_name=clinic.name,
                clinic_address=clinic.address or "",
                clinic_phone=clinic.phone or "",
                clinic_email=clinic.email or "",
                logo_path=Path(clinic.logo_path) if clinic.logo_path else None,
            )
        return ReportConfig(clinic_name="DocAssist Clinic")

    # ========== PDF Reports ==========

    async def generate_daily_summary_pdf(
        self,
        clinic_id: UUID,
        report_date: date,
    ) -> bytes:
        """
        Generate daily summary report PDF.

        Includes:
        - Today's appointments overview
        - Revenue collected
        - No-shows and cancellations
        - Upcoming appointments list
        """
        config = await self._get_clinic_config(clinic_id)
        pdf = PDFReport(config)
        pdf.alias_nb_pages()
        pdf.add_page()

        # Title
        pdf.add_title(
            "Daily Summary Report",
            report_date.strftime("%A, %B %d, %Y")
        )

        # Get data
        stats = await self.analytics.get_appointment_stats(
            clinic_id, report_date, report_date
        )
        revenue = await self.analytics.get_revenue_stats(
            clinic_id, report_date, report_date
        )

        # Key Metrics Section
        pdf.add_section("Today's Overview")
        y = pdf.get_y()

        pdf.add_metric_box("Total Appointments", str(stats.total), 10, y)
        pdf.add_metric_box("Completed", str(stats.completed), 58, y)
        pdf.add_metric_box("No-Shows", str(stats.no_show), 106, y)
        pdf.add_metric_box("Revenue", f"Rs.{revenue.collected:,.0f}", 154, y)

        pdf.set_y(y + 28)

        # Appointment Status Breakdown
        pdf.add_section("Appointment Status")
        pdf.add_table(
            headers=["Status", "Count", "Percentage"],
            rows=[
                ["Completed", stats.completed, f"{stats.completion_rate:.1f}%"],
                ["Scheduled", stats.scheduled, f"{(stats.scheduled/stats.total*100) if stats.total else 0:.1f}%"],
                ["Cancelled", stats.cancelled, f"{stats.cancellation_rate:.1f}%"],
                ["No-Show", stats.no_show, f"{stats.no_show_rate:.1f}%"],
            ],
            col_widths=[70, 50, 70],
        )

        pdf.ln(8)

        # Revenue Summary
        pdf.add_section("Revenue Summary")
        pdf.add_table(
            headers=["Metric", "Amount"],
            rows=[
                ["Total Invoiced", f"Rs.{revenue.total_revenue:,.2f}"],
                ["Collected", f"Rs.{revenue.collected:,.2f}"],
                ["Pending", f"Rs.{revenue.pending:,.2f}"],
                ["Collection Rate", f"{revenue.collection_rate:.1f}%"],
            ],
            col_widths=[95, 95],
        )

        return pdf.output()

    async def generate_monthly_report_pdf(
        self,
        clinic_id: UUID,
        year: int,
        month: int,
    ) -> bytes:
        """
        Generate comprehensive monthly analytics report PDF.

        Includes:
        - Monthly summary metrics
        - Revenue trends
        - Doctor utilization
        - Patient statistics
        - No-show analysis
        """
        config = await self._get_clinic_config(clinic_id)
        pdf = PDFReport(config)
        pdf.alias_nb_pages()
        pdf.add_page()

        # Calculate date range
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        month_name = start_date.strftime("%B %Y")

        # Title
        pdf.add_title("Monthly Analytics Report", month_name)

        # Get all data
        stats = await self.analytics.get_appointment_stats(clinic_id, start_date, end_date)
        revenue = await self.analytics.get_revenue_stats(clinic_id, start_date, end_date)
        doctors = await self.analytics.get_doctor_utilization(clinic_id, start_date, end_date)
        demographics = await self.analytics.get_patient_demographics(clinic_id, start_date)

        # Summary Metrics
        pdf.add_section("Monthly Overview")
        y = pdf.get_y()

        pdf.add_metric_box("Appointments", str(stats.total), 10, y)
        pdf.add_metric_box("Completion Rate", f"{stats.completion_rate:.1f}%", 58, y)
        pdf.add_metric_box("Revenue", f"Rs.{revenue.total_revenue:,.0f}", 106, y)
        pdf.add_metric_box("New Patients", str(demographics.new_this_period), 154, y)

        pdf.set_y(y + 28)

        # Appointment Analysis
        pdf.add_section("Appointment Analysis")
        pdf.add_table(
            headers=["Metric", "Count", "Rate"],
            rows=[
                ["Total Appointments", stats.total, "-"],
                ["Completed", stats.completed, f"{stats.completion_rate:.1f}%"],
                ["Cancelled", stats.cancelled, f"{stats.cancellation_rate:.1f}%"],
                ["No-Shows", stats.no_show, f"{stats.no_show_rate:.1f}%"],
            ],
            col_widths=[80, 50, 60],
        )

        pdf.ln(8)

        # Revenue Analysis
        pdf.add_section("Revenue Analysis")
        pdf.add_table(
            headers=["Metric", "Amount"],
            rows=[
                ["Total Revenue", f"Rs.{revenue.total_revenue:,.2f}"],
                ["Collected", f"Rs.{revenue.collected:,.2f}"],
                ["Pending", f"Rs.{revenue.pending:,.2f}"],
                ["Average Invoice", f"Rs.{revenue.average_invoice:,.2f}"],
                ["Collection Rate", f"{revenue.collection_rate:.1f}%"],
            ],
            col_widths=[95, 95],
        )

        # New page for doctor utilization
        pdf.add_page()
        pdf.add_section("Doctor Utilization")

        if doctors:
            pdf.add_table(
                headers=["Doctor", "Appointments", "Completed", "Utilization"],
                rows=[
                    [d.doctor_name, d.booked_slots, d.completed_appointments, f"{d.utilization_rate:.1f}%"]
                    for d in doctors
                ],
                col_widths=[70, 40, 40, 40],
            )
        else:
            pdf.set_font("Helvetica", "I", 10)
            pdf.cell(0, 10, "No doctor data available", ln=True)

        pdf.ln(8)

        # Patient Demographics
        pdf.add_section("Patient Demographics")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, f"Total Patients: {demographics.total_patients}", ln=True)
        pdf.cell(0, 6, f"New This Month: {demographics.new_this_period}", ln=True)

        if demographics.gender_breakdown:
            pdf.ln(4)
            pdf.add_table(
                headers=["Gender", "Count"],
                rows=[[k.capitalize(), v] for k, v in demographics.gender_breakdown.items()],
                col_widths=[95, 95],
            )

        return pdf.output()

    async def generate_revenue_report_pdf(
        self,
        clinic_id: UUID,
        start_date: date,
        end_date: date,
        doctor_id: Optional[UUID] = None,
    ) -> bytes:
        """Generate detailed revenue report PDF."""
        config = await self._get_clinic_config(clinic_id)
        pdf = PDFReport(config)
        pdf.alias_nb_pages()
        pdf.add_page()

        # Title
        date_range = f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
        pdf.add_title("Revenue Report", date_range)

        # Get data
        revenue = await self.analytics.get_revenue_stats(clinic_id, start_date, end_date, doctor_id)
        daily = await self.analytics.get_daily_metrics(clinic_id, start_date, end_date)

        # Summary
        pdf.add_section("Revenue Summary")
        y = pdf.get_y()

        pdf.add_metric_box("Total Revenue", f"Rs.{revenue.total_revenue:,.0f}", 10, y)
        pdf.add_metric_box("Collected", f"Rs.{revenue.collected:,.0f}", 58, y)
        pdf.add_metric_box("Pending", f"Rs.{revenue.pending:,.0f}", 106, y)
        pdf.add_metric_box("Avg Invoice", f"Rs.{revenue.average_invoice:,.0f}", 154, y)

        pdf.set_y(y + 28)

        # Daily breakdown
        pdf.add_section("Daily Revenue Breakdown")
        pdf.add_table(
            headers=["Date", "Appointments", "Revenue", "New Patients"],
            rows=[
                [d.date.strftime("%b %d"), d.appointments, f"Rs.{d.revenue:,.0f}", d.new_patients]
                for d in daily
            ],
            col_widths=[50, 45, 50, 45],
        )

        return pdf.output()

    # ========== Excel Reports ==========

    async def generate_appointments_excel(
        self,
        clinic_id: UUID,
        start_date: date,
        end_date: date,
        doctor_id: Optional[UUID] = None,
    ) -> bytes:
        """
        Generate appointments Excel report.

        Includes all appointment data with filtering and sorting.
        """
        from sqlalchemy import select, and_

        # Build query
        query = select(
            Appointment, Patient, Doctor
        ).join(
            Patient, Appointment.patient_id == Patient.id
        ).join(
            Doctor, Appointment.doctor_id == Doctor.id
        ).where(
            and_(
                Appointment.clinic_id == clinic_id,
                Appointment.scheduled_start >= datetime.combine(start_date, datetime.min.time()),
                Appointment.scheduled_start <= datetime.combine(end_date, datetime.max.time()),
            )
        )

        if doctor_id:
            query = query.where(Appointment.doctor_id == doctor_id)

        result = await self.db.execute(query.order_by(Appointment.scheduled_start))
        rows = result.all()

        # Create DataFrame
        data = []
        for appt, patient, doctor in rows:
            data.append({
                "Date": appt.scheduled_start.strftime("%Y-%m-%d"),
                "Time": appt.scheduled_start.strftime("%H:%M"),
                "Patient Name": f"{patient.first_name} {patient.last_name or ''}".strip(),
                "Patient Phone": patient.phone,
                "Doctor": doctor.name,
                "Type": appt.appointment_type.value if appt.appointment_type else "Consultation",
                "Status": appt.status.value if appt.status else "Scheduled",
                "Duration (min)": appt.duration_minutes or 15,
                "Notes": appt.notes or "",
            })

        df = pd.DataFrame(data)

        # Create Excel workbook
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Appointments", index=False)

            # Get workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets["Appointments"]

            # Style header row
            header_fill = PatternFill(start_color="2980B9", end_color="2980B9", fill_type="solid")
            header_font = Font(color="FFFFFF", bold=True)

            for cell in worksheet[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center")

            # Adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width

        output.seek(0)
        return output.getvalue()

    async def generate_revenue_excel(
        self,
        clinic_id: UUID,
        start_date: date,
        end_date: date,
    ) -> bytes:
        """
        Generate comprehensive revenue Excel report.

        Includes:
        - Summary sheet
        - Daily breakdown
        - Invoice details
        """
        # Get data
        revenue = await self.analytics.get_revenue_stats(clinic_id, start_date, end_date)
        daily = await self.analytics.get_daily_metrics(clinic_id, start_date, end_date)

        output = io.BytesIO()
        workbook = Workbook()

        # ===== Summary Sheet =====
        ws_summary = workbook.active
        ws_summary.title = "Summary"

        # Header styling
        header_fill = PatternFill(start_color="2980B9", end_color="2980B9", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True, size=12)

        # Title
        ws_summary["A1"] = "Revenue Report"
        ws_summary["A1"].font = Font(bold=True, size=16)
        ws_summary["A2"] = f"Period: {start_date.strftime('%b %d, %Y')} - {end_date.strftime('%b %d, %Y')}"

        # Summary metrics
        summary_data = [
            ["Metric", "Value"],
            ["Total Revenue", f"Rs.{revenue.total_revenue:,.2f}"],
            ["Collected", f"Rs.{revenue.collected:,.2f}"],
            ["Pending", f"Rs.{revenue.pending:,.2f}"],
            ["Average Invoice", f"Rs.{revenue.average_invoice:,.2f}"],
            ["Collection Rate", f"{revenue.collection_rate:.1f}%"],
        ]

        for row_idx, row_data in enumerate(summary_data, start=4):
            for col_idx, value in enumerate(row_data, start=1):
                cell = ws_summary.cell(row=row_idx, column=col_idx, value=value)
                if row_idx == 4:
                    cell.fill = header_fill
                    cell.font = header_font

        ws_summary.column_dimensions["A"].width = 20
        ws_summary.column_dimensions["B"].width = 20

        # ===== Daily Breakdown Sheet =====
        ws_daily = workbook.create_sheet("Daily Breakdown")

        daily_data = [
            ["Date", "Appointments", "Revenue", "New Patients"]
        ]
        for d in daily:
            daily_data.append([
                d.date.strftime("%Y-%m-%d"),
                d.appointments,
                float(d.revenue),
                d.new_patients,
            ])

        for row_idx, row_data in enumerate(daily_data, start=1):
            for col_idx, value in enumerate(row_data, start=1):
                cell = ws_daily.cell(row=row_idx, column=col_idx, value=value)
                if row_idx == 1:
                    cell.fill = header_fill
                    cell.font = header_font

        # Add chart
        if len(daily) > 1:
            chart = BarChart()
            chart.title = "Daily Revenue"
            chart.y_axis.title = "Revenue (Rs.)"
            chart.x_axis.title = "Date"

            data = Reference(ws_daily, min_col=3, min_row=1, max_row=len(daily) + 1)
            cats = Reference(ws_daily, min_col=1, min_row=2, max_row=len(daily) + 1)
            chart.add_data(data, titles_from_data=True)
            chart.set_categories(cats)
            chart.width = 15
            chart.height = 8

            ws_daily.add_chart(chart, "F2")

        for col in ["A", "B", "C", "D"]:
            ws_daily.column_dimensions[col].width = 15

        workbook.save(output)
        output.seek(0)
        return output.getvalue()

    async def generate_doctor_utilization_excel(
        self,
        clinic_id: UUID,
        start_date: date,
        end_date: date,
    ) -> bytes:
        """Generate doctor utilization Excel report."""
        doctors = await self.analytics.get_doctor_utilization(clinic_id, start_date, end_date)

        data = []
        for d in doctors:
            data.append({
                "Doctor": d.doctor_name,
                "Total Slots": d.total_slots,
                "Booked Slots": d.booked_slots,
                "Completed": d.completed_appointments,
                "Utilization Rate": f"{d.utilization_rate:.1f}%",
                "Avg Duration (min)": round(d.average_duration_minutes, 1),
            })

        df = pd.DataFrame(data)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Doctor Utilization", index=False)

            # Style
            workbook = writer.book
            worksheet = writer.sheets["Doctor Utilization"]

            header_fill = PatternFill(start_color="2980B9", end_color="2980B9", fill_type="solid")
            header_font = Font(color="FFFFFF", bold=True)

            for cell in worksheet[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center")

            for column in worksheet.columns:
                max_length = max(len(str(cell.value or "")) for cell in column)
                worksheet.column_dimensions[column[0].column_letter].width = min(max_length + 2, 25)

        output.seek(0)
        return output.getvalue()

    async def generate_patient_demographics_excel(
        self,
        clinic_id: UUID,
    ) -> bytes:
        """Generate patient demographics Excel report."""
        demographics = await self.analytics.get_patient_demographics(clinic_id)

        output = io.BytesIO()
        workbook = Workbook()

        # Summary sheet
        ws = workbook.active
        ws.title = "Demographics"

        header_fill = PatternFill(start_color="2980B9", end_color="2980B9", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)

        # Summary
        ws["A1"] = "Patient Demographics Report"
        ws["A1"].font = Font(bold=True, size=16)

        ws["A3"] = "Total Patients"
        ws["B3"] = demographics.total_patients

        # Gender breakdown
        ws["A5"] = "Gender Breakdown"
        ws["A5"].font = Font(bold=True, size=12)

        row = 6
        ws.cell(row=row, column=1, value="Gender").fill = header_fill
        ws.cell(row=row, column=1).font = header_font
        ws.cell(row=row, column=2, value="Count").fill = header_fill
        ws.cell(row=row, column=2).font = header_font

        for gender, count in demographics.gender_breakdown.items():
            row += 1
            ws.cell(row=row, column=1, value=gender.capitalize())
            ws.cell(row=row, column=2, value=count)

        # City breakdown
        row += 2
        ws.cell(row=row, column=1, value="City Breakdown").font = Font(bold=True, size=12)

        row += 1
        ws.cell(row=row, column=1, value="City").fill = header_fill
        ws.cell(row=row, column=1).font = header_font
        ws.cell(row=row, column=2, value="Count").fill = header_fill
        ws.cell(row=row, column=2).font = header_font

        for city, count in sorted(demographics.city_breakdown.items(), key=lambda x: -x[1])[:20]:
            row += 1
            ws.cell(row=row, column=1, value=city or "Unknown")
            ws.cell(row=row, column=2, value=count)

        ws.column_dimensions["A"].width = 25
        ws.column_dimensions["B"].width = 15

        workbook.save(output)
        output.seek(0)
        return output.getvalue()


def get_report_service(db: AsyncSession) -> ReportService:
    """Factory function for report service."""
    return ReportService(db)
