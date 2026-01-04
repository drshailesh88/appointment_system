"""
EMR Sync Service with Background Job.

Provides real-time synchronization between Practice Manager and DocAssist EMR.
Uses watchdog for file system monitoring and scheduled background jobs.
"""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.integrations.emr import EMRIntegration, EMRIntegrationAsync, EMRPatient, EMRVisit
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.models.procedure import Procedure

logger = logging.getLogger(__name__)


class EMRSyncService:
    """
    EMR Synchronization Service.

    Handles:
    - Real-time sync via file system watching
    - Scheduled background sync every N minutes
    - Bidirectional appointment sync
    - One-way patient data sync (EMR -> PM)
    - Conflict resolution (EMR wins for clinical, PM wins for scheduling)
    """

    def __init__(self):
        """Initialize EMR sync service."""
        emr_path = Path(settings.emr_database_path) if settings.emr_database_path else None
        self.emr = EMRIntegration(emr_path)
        self.emr_async = EMRIntegrationAsync(emr_path)

        self._sync_running = False
        self._last_sync_time: Optional[datetime] = None
        self._sync_stats = {
            "patients_synced": 0,
            "visits_synced": 0,
            "appointments_synced": 0,
            "errors": [],
            "last_sync_duration_seconds": 0.0,
        }

    def is_available(self) -> bool:
        """Check if EMR integration is available and enabled."""
        return settings.emr_sync_enabled and self.emr.is_available()

    def get_status(self) -> dict:
        """Get current sync status."""
        return {
            "enabled": settings.emr_sync_enabled,
            "available": self.emr.is_available(),
            "database_path": str(self.emr.db_path) if self.emr.db_path else None,
            "last_sync_time": self._last_sync_time.isoformat() if self._last_sync_time else None,
            "sync_running": self._sync_running,
            "stats": self._sync_stats,
            "sync_interval_seconds": settings.emr_sync_interval_seconds,
        }

    async def sync_patient_from_emr(
        self,
        patient_id: str,
        db: AsyncSession,
    ) -> Optional[Patient]:
        """
        Sync a patient from EMR to Practice Manager.

        EMR is the source of truth for patient demographics.
        """
        emr_patient = await self.emr_async.get_patient(patient_id)
        if not emr_patient:
            return None

        # Check if patient already exists in PM
        stmt = select(Patient).where(Patient.emr_patient_id == patient_id)
        result = await db.execute(stmt)
        patient = result.scalar_one_or_none()

        if patient:
            # Update existing patient with EMR data
            patient.first_name = emr_patient.first_name
            patient.last_name = emr_patient.last_name
            patient.phone = emr_patient.phone
            patient.email = emr_patient.email
            patient.date_of_birth = emr_patient.date_of_birth
            patient.gender = emr_patient.gender
            patient.blood_group = emr_patient.blood_group
            patient.allergies = emr_patient.allergies
            patient.address = emr_patient.address
            patient.emr_synced_at = datetime.now(timezone.utc)

            logger.info(f"Updated patient {patient_id} from EMR")
        else:
            # Create new patient from EMR data
            patient = Patient(
                emr_patient_id=patient_id,
                first_name=emr_patient.first_name,
                last_name=emr_patient.last_name,
                phone=emr_patient.phone,
                email=emr_patient.email,
                date_of_birth=emr_patient.date_of_birth,
                gender=emr_patient.gender,
                blood_group=emr_patient.blood_group,
                allergies=emr_patient.allergies,
                address=emr_patient.address,
                emr_synced_at=datetime.now(timezone.utc),
            )
            db.add(patient)
            logger.info(f"Created new patient {patient_id} from EMR")

        await db.commit()
        await db.refresh(patient)
        return patient

    async def sync_appointment_to_emr(
        self,
        appointment: Appointment,
        db: AsyncSession,
    ) -> bool:
        """
        Sync an appointment from Practice Manager to EMR.

        Creates a placeholder appointment record in EMR.
        """
        if not self.is_available():
            return False

        # Get patient's EMR ID
        stmt = select(Patient).where(Patient.id == appointment.patient_id)
        result = await db.execute(stmt)
        patient = result.scalar_one_or_none()

        if not patient or not patient.emr_patient_id:
            logger.warning(f"Patient {appointment.patient_id} not linked to EMR")
            return False

        # Sync to EMR
        success = self.emr.sync_appointment_to_emr(
            appointment_id=str(appointment.id),
            patient_id=patient.emr_patient_id,
            doctor_name=appointment.doctor.name if appointment.doctor else "Unknown",
            scheduled_start=appointment.scheduled_start,
            appointment_type=appointment.appointment_type,
            chief_complaint=appointment.chief_complaint,
        )

        if success:
            logger.info(f"Synced appointment {appointment.id} to EMR")

        return success

    async def link_appointment_to_visit(
        self,
        appointment_id: str,
        emr_visit_id: str,
        db: AsyncSession,
    ) -> bool:
        """
        Link an appointment to its EMR visit after consultation.

        Updates both PM and EMR databases.
        """
        # Update PM database
        stmt = select(Appointment).where(Appointment.id == appointment_id)
        result = await db.execute(stmt)
        appointment = result.scalar_one_or_none()

        if not appointment:
            return False

        appointment.emr_visit_id = emr_visit_id
        await db.commit()

        # Update EMR database
        success = self.emr.link_appointment_to_visit(appointment_id, emr_visit_id)

        if success:
            logger.info(f"Linked appointment {appointment_id} to visit {emr_visit_id}")

        return success

    async def full_sync(self, db: AsyncSession) -> dict:
        """
        Perform a full bidirectional sync.

        1. Sync patients from EMR to PM
        2. Sync new/modified appointments to EMR
        3. Link completed appointments to EMR visits

        Returns sync statistics.
        """
        if not self.is_available():
            return {
                "error": "EMR sync not available",
                "enabled": settings.emr_sync_enabled,
                "available": self.emr.is_available(),
            }

        if self._sync_running:
            return {"error": "Sync already in progress"}

        self._sync_running = True
        start_time = datetime.now(timezone.utc)

        stats = {
            "patients_synced": 0,
            "appointments_synced": 0,
            "visits_linked": 0,
            "errors": [],
        }

        try:
            # 1. Sync patients from EMR
            logger.info("Starting patient sync from EMR...")
            since = self._last_sync_time or datetime(2000, 1, 1, tzinfo=timezone.utc)
            emr_patients = self.emr.get_patients_updated_since(since)

            for emr_patient in emr_patients:
                try:
                    await self.sync_patient_from_emr(emr_patient.id, db)
                    stats["patients_synced"] += 1
                except Exception as e:
                    error_msg = f"Error syncing patient {emr_patient.id}: {str(e)}"
                    logger.error(error_msg)
                    stats["errors"].append(error_msg)

            # 2. Sync recent appointments to EMR
            logger.info("Starting appointment sync to EMR...")
            cutoff_time = datetime.now(timezone.utc)
            if self._last_sync_time:
                cutoff_time = self._last_sync_time

            stmt = select(Appointment).where(
                Appointment.updated_at > cutoff_time
            )
            result = await db.execute(stmt)
            appointments = result.scalars().all()

            for appointment in appointments:
                try:
                    success = await self.sync_appointment_to_emr(appointment, db)
                    if success:
                        stats["appointments_synced"] += 1
                except Exception as e:
                    error_msg = f"Error syncing appointment {appointment.id}: {str(e)}"
                    logger.error(error_msg)
                    stats["errors"].append(error_msg)

            # 3. Link completed appointments to EMR visits
            logger.info("Linking appointments to visits...")
            stmt = select(Appointment).where(
                Appointment.status == "completed",
                Appointment.emr_visit_id.is_(None),
            )
            result = await db.execute(stmt)
            completed_appointments = result.scalars().all()

            for appointment in completed_appointments:
                try:
                    # Get patient's EMR ID
                    patient_stmt = select(Patient).where(Patient.id == appointment.patient_id)
                    patient_result = await db.execute(patient_stmt)
                    patient = patient_result.scalar_one_or_none()

                    if patient and patient.emr_patient_id:
                        # Check if there's a visit in EMR for this patient around the appointment time
                        visits = await self.emr_async.get_patient_visits(patient.emr_patient_id, limit=5)

                        for visit in visits:
                            visit_date = datetime.fromisoformat(visit.visit_date)
                            # If visit date matches appointment date (within same day)
                            if visit_date.date() == appointment.scheduled_start.date():
                                await self.link_appointment_to_visit(
                                    str(appointment.id),
                                    visit.id,
                                    db,
                                )
                                stats["visits_linked"] += 1
                                break

                except Exception as e:
                    error_msg = f"Error linking appointment {appointment.id}: {str(e)}"
                    logger.error(error_msg)
                    stats["errors"].append(error_msg)

            # Update sync metadata
            self._last_sync_time = start_time
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            self._sync_stats = {
                **stats,
                "last_sync_duration_seconds": duration,
            }

            logger.info(
                f"EMR sync completed in {duration:.2f}s: "
                f"{stats['patients_synced']} patients, "
                f"{stats['appointments_synced']} appointments, "
                f"{stats['visits_linked']} visits linked, "
                f"{len(stats['errors'])} errors"
            )

        except Exception as e:
            error_msg = f"Full sync failed: {str(e)}"
            logger.error(error_msg)
            stats["errors"].append(error_msg)

        finally:
            self._sync_running = False

        return stats

    def start_file_watcher(self):
        """Start watching EMR database file for changes."""
        if not self.is_available():
            logger.warning("EMR not available, file watcher not started")
            return

        try:
            self.emr.start_watcher()
            logger.info("EMR file watcher started")
        except Exception as e:
            logger.error(f"Failed to start EMR file watcher: {e}")

    def stop_file_watcher(self):
        """Stop the file watcher."""
        try:
            self.emr.stop_watcher()
            logger.info("EMR file watcher stopped")
        except Exception as e:
            logger.error(f"Failed to stop EMR file watcher: {e}")


# Global singleton instance
_emr_sync_service: Optional[EMRSyncService] = None


def get_emr_sync_service() -> EMRSyncService:
    """Get or create the global EMR sync service instance."""
    global _emr_sync_service
    if _emr_sync_service is None:
        _emr_sync_service = EMRSyncService()
    return _emr_sync_service
