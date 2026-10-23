import os
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
from app.core.config import settings
from app.models.prescription import PrescriptionInDB
from app.models.patient import PatientInDB
from app.models.doctor import DoctorInDB

logger = logging.getLogger("healthcare_system")


class PrescriptionPDFError(Exception):
    pass


class PrescriptionPDFService:
    def __init__(self):
        self.upload_dir = os.path.join(settings.upload_dir, "prescriptions")
        os.makedirs(self.upload_dir, exist_ok=True)

    def _safe_filename(self) -> str:
        return f"prescription_{uuid.uuid4().hex}.pdf"

    def generate(self, prescription: PrescriptionInDB, patient: Optional[PatientInDB], doctor: Optional[DoctorInDB], verify_url: Optional[str] = None) -> str:
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        except ImportError as exc:
            raise PrescriptionPDFError("ReportLab is not installed") from exc

        filename = self._safe_filename()
        full_path = os.path.join(self.upload_dir, filename)

        try:
            doc = SimpleDocTemplate(full_path, pagesize=letter)
            styles = getSampleStyleSheet()
            elements = []

            title_style = ParagraphStyle(
                "Title",
                parent=styles["Title"],
                fontSize=20,
                textColor=colors.HexColor("#2563eb"),
                spaceAfter=6,
            )
            subtitle_style = ParagraphStyle(
                "Subtitle",
                parent=styles["Normal"],
                fontSize=10,
                textColor=colors.HexColor("#6b7280"),
                spaceAfter=18,
            )

            elements.append(Paragraph("Healthcare System", title_style))
            elements.append(Paragraph("Digital Prescription", subtitle_style))
            elements.append(Spacer(1, 12))

            prescription_date_str = ""
            if prescription.prescription_date:
                prescription_date_str = prescription.prescription_date.strftime("%Y-%m-%d %H:%M")

            info_data = [
                ["Prescription ID:", prescription.id],
                ["Date:", prescription_date_str],
                ["Status:", prescription.status.title()],
            ]
            info_table = Table(info_data, colWidths=[120, 300])
            info_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]))
            elements.append(info_table)
            elements.append(Spacer(1, 14))

            elements.append(Paragraph("<b>Doctor</b>", styles["Heading2"]))
            doctor_name = doctor.full_name if doctor else "N/A"
            doctor_phone = doctor.contact_phone if doctor else "N/A"
            doctor_email = doctor.contact_email if doctor else "N/A"
            doctor_specialization = doctor.specialization if doctor else "N/A"

            doctor_data = [
                ["Name:", doctor_name],
                ["Specialization:", doctor_specialization],
                ["Phone:", doctor_phone],
                ["Email:", doctor_email],
            ]
            doctor_table = Table(doctor_data, colWidths=[120, 300])
            doctor_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
            ]))
            elements.append(doctor_table)
            elements.append(Spacer(1, 14))

            elements.append(Paragraph("<b>Patient</b>", styles["Heading2"]))
            patient_name = patient.full_name if patient else "N/A"
            patient_dob = patient.date_of_birth.strftime("%Y-%m-%d") if patient and patient.date_of_birth else "N/A"
            patient_gender = patient.gender if patient and patient.gender else "N/A"
            patient_phone = patient.contact_phone if patient else "N/A"

            patient_data = [
                ["Name:", patient_name],
                ["Date of Birth:", patient_dob],
                ["Gender:", patient_gender],
                ["Contact:", patient_phone],
            ]
            patient_table = Table(patient_data, colWidths=[120, 300])
            patient_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
            ]))
            elements.append(patient_table)
            elements.append(Spacer(1, 14))

            elements.append(Paragraph("<b>Medicines</b>", styles["Heading2"]))
            medicine_data = [["Medicine", "Dosage", "Frequency", "Duration", "Route", "Instructions"]]
            for item in prescription.items:
                if isinstance(item, dict):
                    medicine_data.append([
                        item.get("medicine_name", ""),
                        item.get("dosage", ""),
                        item.get("frequency", ""),
                        item.get("duration", ""),
                        item.get("route") or "",
                        item.get("instructions") or "",
                    ])
                else:
                    medicine_data.append([
                        item.medicine_name,
                        item.dosage,
                        item.frequency,
                        item.duration,
                        item.route or "",
                        item.instructions or "",
                    ])

            medicine_table = Table(medicine_data, colWidths=[100, 70, 80, 70, 60, 140])
            medicine_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            elements.append(medicine_table)
            elements.append(Spacer(1, 14))

            if prescription.diagnosis_notes:
                elements.append(Paragraph("<b>Clinical Notes</b>", styles["Heading2"]))
                elements.append(Paragraph(prescription.diagnosis_notes, styles["Normal"]))
                elements.append(Spacer(1, 10))

            if prescription.advice:
                elements.append(Paragraph("<b>General Instructions</b>", styles["Heading2"]))
                elements.append(Paragraph(prescription.advice, styles["Normal"]))
                elements.append(Spacer(1, 10))

            if prescription.follow_up_date:
                follow_up_str = prescription.follow_up_date.strftime("%Y-%m-%d")
                elements.append(Paragraph(f"<b>Follow-up Date:</b> {follow_up_str}", styles["Normal"]))
                elements.append(Spacer(1, 10))

            generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            elements.append(Spacer(1, 20))
            elements.append(Paragraph(f"<i>Generated: {generated_at}</i>", styles["Normal"]))
            elements.append(Paragraph("<i>Digitally generated prescription.</i>", styles["Normal"]))

            if verify_url:
                elements.append(Spacer(1, 14))
                elements.append(Paragraph("<b>Verify this prescription</b>", styles["Heading2"]))
                try:
                    from reportlab.graphics.barcode.qr import QrCodeWidget
                    from reportlab.graphics.shapes import Drawing

                    qr = QrCodeWidget(verify_url)
                    drawing = Drawing(130, 130)
                    drawing.add(qr)
                    elements.append(drawing)
                except Exception as exc:
                    logger.warning(f"QR embed failed (non-fatal): {exc}")
                elements.append(Paragraph(
                    f'Scan the code or visit: <a href="{verify_url}">{verify_url}</a>',
                    styles["Normal"],
                ))

            doc.build(elements)
            return full_path
        except PrescriptionPDFError:
            raise
        except Exception as exc:
            logger.error(f"Failed to generate prescription PDF: {exc}")
            raise PrescriptionPDFError("Failed to generate prescription PDF") from exc

    def generate_emergency_card(self, patient: PatientInDB, verify_url: str) -> str:
        """Printable emergency card: blood group, allergies, emergency contact
        + QR to the revocable public page. No other data is included."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        except ImportError as exc:
            raise PrescriptionPDFError("ReportLab is not installed") from exc

        filename = self._safe_filename()
        full_path = os.path.join(self.upload_dir, filename)
        try:
            doc = SimpleDocTemplate(full_path, pagesize=letter)
            styles = getSampleStyleSheet()
            elements = []
            title_style = ParagraphStyle(
                "EmergencyTitle", parent=styles["Title"], fontSize=22,
                textColor=colors.HexColor("#b91c1c"), spaceAfter=4,
            )
            elements.append(Paragraph("EMERGENCY CARD", title_style))
            elements.append(Paragraph(
                "Show this to first responders. Verify online via the QR code below.",
                styles["Normal"],
            ))
            elements.append(Spacer(1, 12))

            allergies = ", ".join(patient.allergies or []) or "None recorded"
            rows = [
                ["Blood Group:", patient.blood_group or "Not recorded"],
                ["Allergies:", allergies],
                ["Emergency Contact:", patient.emergency_contact_name or "Not recorded"],
                ["Contact Phone:", patient.emergency_contact_phone or "Not recorded"],
            ]
            table = Table(rows, colWidths=[140, 320])
            table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 12),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 14))
            try:
                from reportlab.graphics.barcode.qr import QrCodeWidget
                from reportlab.graphics.shapes import Drawing

                drawing = Drawing(130, 130)
                drawing.add(QrCodeWidget(verify_url))
                elements.append(drawing)
            except Exception as exc:
                logger.warning(f"Emergency QR embed failed (non-fatal): {exc}")
            elements.append(Paragraph(
                f'Online emergency page: <a href="{verify_url}">{verify_url}</a><br/>'
                "You can revoke this link anytime from your profile.",
                styles["Normal"],
            ))
            doc.build(elements)
            return full_path
        except PrescriptionPDFError:
            raise
        except Exception as exc:
            logger.error(f"Failed to generate emergency card: {exc}")
            raise PrescriptionPDFError("Failed to generate emergency card") from exc
