"""
EMR Integration Module.

Syncs with DocAssist EMR (https://github.com/drshailesh88/emr) which is:
- Built with Python/Flet
- Uses SQLite for local storage
- Stores patient records, clinical notes, prescriptions

Sync Strategy:
- Read patient data from EMR (one-way)
- Sync appointments bidirectionally
- Use file system watcher (watchdog) for real-time updates
- Queue changes for offline resilience
"""

import asyncio
import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import Any, Callable, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)

# Default EMR database paths (configurable)
EMR_DATA_PATHS = [
    Path.home() / ".docassist_emr" / "data" / "emr.db",
    Path.home() / "DocAssist" / "emr.db",
    Path("/var/lib/docassist/emr.db"),
]


@dataclass
class EMRPatient:
    """Patient record from EMR."""

    id: str
    first_name: str
    last_name: Optional[str]
    phone: str
    email: Optional[str]
    date_of_birth: Optional[str]
    gender: Optional[str]
    blood_group: Optional[str]
    allergies: Optional[str]
    address: Optional[str]
    created_at: str
    updated_at: str


@dataclass
class EMRVisit:
    """Visit/consultation record from EMR."""

    id: str
    patient_id: str
    doctor_name: str
    visit_date: str
    chief_complaint: Optional[str]
    diagnosis: Optional[str]
    notes: Optional[str]
    vitals: Optional[dict]
    prescriptions: Optional[list]
    created_at: str


@dataclass
class SyncEvent:
    """Event representing a data change."""

    event_type: str  # "patient_created", "patient_updated", "visit_created"
    entity_type: str  # "patient", "visit", "prescription"
    entity_id: str
    data: dict
    timestamp: datetime


class EMRIntegration:
    """
    EMR Integration service.

    Provides:
    - Patient data sync (EMR -> Practice Manager)
    - Visit/appointment sync (bidirectional)
    - Real-time file watching for changes
    """

    def __init__(
        self,
        emr_db_path: Optional[Path] = None,
        on_patient_sync: Optional[Callable[[EMRPatient], None]] = None,
        on_visit_sync: Optional[Callable[[EMRVisit], None]] = None,
    ):
        """
        Initialize EMR integration.

        Args:
            emr_db_path: Path to EMR SQLite database
            on_patient_sync: Callback when patient is synced
            on_visit_sync: Callback when visit is synced
        """
        self.db_path = emr_db_path or self._find_emr_database()
        self.on_patient_sync = on_patient_sync
        self.on_visit_sync = on_visit_sync

        self._sync_queue: Queue[SyncEvent] = Queue()
        self._watcher_thread: Optional[Thread] = None
        self._running = False

        # Last sync timestamps
        self._last_patient_sync: Optional[datetime] = None
        self._last_visit_sync: Optional[datetime] = None

    def _find_emr_database(self) -> Optional[Path]:
        """Find the EMR database file."""
        for path in EMR_DATA_PATHS:
            if path.exists():
                logger.info(f"Found EMR database at: {path}")
                return path

        logger.warning("EMR database not found. Integration disabled.")
        return None

    def is_available(self) -> bool:
        """Check if EMR integration is available."""
        return self.db_path is not None and self.db_path.exists()

    def get_connection(self) -> Optional[sqlite3.Connection]:
        """Get SQLite connection to EMR database."""
        if not self.is_available():
            return None

        try:
            conn = sqlite3.connect(str(self.db_path), timeout=5.0)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            logger.error(f"Failed to connect to EMR database: {e}")
            return None

    # ==================
    # Patient Sync
    # ==================

    def get_patient(self, patient_id: str) -> Optional[EMRPatient]:
        """Get a patient from EMR by ID."""
        conn = self.get_connection()
        if not conn:
            return None

        try:
            cursor = conn.execute(
                "SELECT * FROM patients WHERE id = ?",
                (patient_id,),
            )
            row = cursor.fetchone()

            if row:
                return self._row_to_patient(row)
            return None

        except sqlite3.Error as e:
            logger.error(f"Error fetching patient: {e}")
            return None
        finally:
            conn.close()

    def search_patients(
        self,
        query: str,
        limit: int = 20,
    ) -> list[EMRPatient]:
        """Search patients in EMR."""
        conn = self.get_connection()
        if not conn:
            return []

        try:
            cursor = conn.execute(
                """
                SELECT * FROM patients
                WHERE first_name LIKE ? OR last_name LIKE ? OR phone LIKE ?
                LIMIT ?
                """,
                (f"%{query}%", f"%{query}%", f"%{query}%", limit),
            )
            rows = cursor.fetchall()

            return [self._row_to_patient(row) for row in rows]

        except sqlite3.Error as e:
            logger.error(f"Error searching patients: {e}")
            return []
        finally:
            conn.close()

    def get_patients_updated_since(
        self,
        since: datetime,
    ) -> list[EMRPatient]:
        """Get patients updated since a timestamp."""
        conn = self.get_connection()
        if not conn:
            return []

        try:
            cursor = conn.execute(
                """
                SELECT * FROM patients
                WHERE updated_at > ?
                ORDER BY updated_at ASC
                """,
                (since.isoformat(),),
            )
            rows = cursor.fetchall()

            return [self._row_to_patient(row) for row in rows]

        except sqlite3.Error as e:
            logger.error(f"Error fetching updated patients: {e}")
            return []
        finally:
            conn.close()

    def _row_to_patient(self, row: sqlite3.Row) -> EMRPatient:
        """Convert database row to EMRPatient."""
        return EMRPatient(
            id=row["id"],
            first_name=row["first_name"],
            last_name=row.get("last_name"),
            phone=row["phone"],
            email=row.get("email"),
            date_of_birth=row.get("date_of_birth"),
            gender=row.get("gender"),
            blood_group=row.get("blood_group"),
            allergies=row.get("allergies"),
            address=row.get("address"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    # ==================
    # Visit/Clinical Sync
    # ==================

    def get_patient_visits(
        self,
        patient_id: str,
        limit: int = 10,
    ) -> list[EMRVisit]:
        """Get visits for a patient from EMR."""
        conn = self.get_connection()
        if not conn:
            return []

        try:
            cursor = conn.execute(
                """
                SELECT * FROM visits
                WHERE patient_id = ?
                ORDER BY visit_date DESC
                LIMIT ?
                """,
                (patient_id, limit),
            )
            rows = cursor.fetchall()

            return [self._row_to_visit(row) for row in rows]

        except sqlite3.Error as e:
            logger.error(f"Error fetching visits: {e}")
            return []
        finally:
            conn.close()

    def get_visit(self, visit_id: str) -> Optional[EMRVisit]:
        """Get a specific visit from EMR."""
        conn = self.get_connection()
        if not conn:
            return None

        try:
            cursor = conn.execute(
                "SELECT * FROM visits WHERE id = ?",
                (visit_id,),
            )
            row = cursor.fetchone()

            if row:
                return self._row_to_visit(row)
            return None

        except sqlite3.Error as e:
            logger.error(f"Error fetching visit: {e}")
            return None
        finally:
            conn.close()

    def _row_to_visit(self, row: sqlite3.Row) -> EMRVisit:
        """Convert database row to EMRVisit."""
        vitals = None
        if row.get("vitals"):
            try:
                vitals = json.loads(row["vitals"])
            except json.JSONDecodeError:
                pass

        prescriptions = None
        if row.get("prescriptions"):
            try:
                prescriptions = json.loads(row["prescriptions"])
            except json.JSONDecodeError:
                pass

        return EMRVisit(
            id=row["id"],
            patient_id=row["patient_id"],
            doctor_name=row.get("doctor_name", "Unknown"),
            visit_date=row["visit_date"],
            chief_complaint=row.get("chief_complaint"),
            diagnosis=row.get("diagnosis"),
            notes=row.get("notes"),
            vitals=vitals,
            prescriptions=prescriptions,
            created_at=row["created_at"],
        )

    # ==================
    # Appointment Sync (Bidirectional)
    # ==================

    def sync_appointment_to_emr(
        self,
        appointment_id: str,
        patient_id: str,
        doctor_name: str,
        scheduled_start: datetime,
        appointment_type: str,
        chief_complaint: Optional[str] = None,
    ) -> bool:
        """
        Sync an appointment from Practice Manager to EMR.

        Creates a placeholder visit record in EMR.
        """
        conn = self.get_connection()
        if not conn:
            return False

        try:
            # Check if appointment already synced
            cursor = conn.execute(
                "SELECT id FROM appointments WHERE external_id = ?",
                (appointment_id,),
            )
            if cursor.fetchone():
                # Update existing
                conn.execute(
                    """
                    UPDATE appointments
                    SET scheduled_time = ?, updated_at = ?
                    WHERE external_id = ?
                    """,
                    (
                        scheduled_start.isoformat(),
                        datetime.now(timezone.utc).isoformat(),
                        appointment_id,
                    ),
                )
            else:
                # Insert new
                conn.execute(
                    """
                    INSERT INTO appointments
                    (id, external_id, patient_id, doctor_name, scheduled_time,
                     appointment_type, chief_complaint, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        appointment_id,
                        patient_id,
                        doctor_name,
                        scheduled_start.isoformat(),
                        appointment_type,
                        chief_complaint,
                        "scheduled",
                        datetime.now(timezone.utc).isoformat(),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )

            conn.commit()
            logger.info(f"Synced appointment {appointment_id} to EMR")
            return True

        except sqlite3.Error as e:
            logger.error(f"Error syncing appointment to EMR: {e}")
            return False
        finally:
            conn.close()

    def link_appointment_to_visit(
        self,
        appointment_id: str,
        visit_id: str,
    ) -> bool:
        """Link an appointment to its EMR visit after consultation."""
        conn = self.get_connection()
        if not conn:
            return False

        try:
            conn.execute(
                """
                UPDATE appointments
                SET visit_id = ?, status = ?, updated_at = ?
                WHERE external_id = ?
                """,
                (
                    visit_id,
                    "completed",
                    datetime.now(timezone.utc).isoformat(),
                    appointment_id,
                ),
            )
            conn.commit()
            return True

        except sqlite3.Error as e:
            logger.error(f"Error linking appointment to visit: {e}")
            return False
        finally:
            conn.close()

    # ==================
    # File System Watcher
    # ==================

    def start_watcher(self):
        """Start watching EMR database for changes."""
        if not self.is_available():
            logger.warning("EMR database not available. Watcher not started.")
            return

        if self._running:
            logger.warning("Watcher already running")
            return

        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer

            class EMREventHandler(FileSystemEventHandler):
                def __init__(self, integration: "EMRIntegration"):
                    self.integration = integration

                def on_modified(self, event):
                    if event.src_path.endswith(".db"):
                        logger.info("EMR database modified, triggering sync")
                        self.integration._queue_sync()

            self._running = True
            self._observer = Observer()
            self._observer.schedule(
                EMREventHandler(self),
                str(self.db_path.parent),
                recursive=False,
            )
            self._observer.start()
            logger.info("EMR file watcher started")

        except ImportError:
            logger.warning("watchdog not installed. Real-time sync disabled.")

    def stop_watcher(self):
        """Stop the file system watcher."""
        self._running = False
        if hasattr(self, "_observer"):
            self._observer.stop()
            self._observer.join()
            logger.info("EMR file watcher stopped")

    def _queue_sync(self):
        """Queue a sync event."""
        event = SyncEvent(
            event_type="database_modified",
            entity_type="all",
            entity_id="",
            data={},
            timestamp=datetime.now(timezone.utc),
        )
        self._sync_queue.put(event)

    # ==================
    # Full Sync
    # ==================

    async def full_sync(
        self,
        on_progress: Optional[Callable[[str, int, int], None]] = None,
    ) -> dict:
        """
        Perform a full sync with EMR.

        Args:
            on_progress: Callback(entity_type, current, total)

        Returns:
            Sync statistics
        """
        if not self.is_available():
            return {"error": "EMR not available", "synced": False}

        stats = {
            "patients_synced": 0,
            "visits_synced": 0,
            "errors": [],
        }

        # Sync patients
        try:
            since = self._last_patient_sync or datetime(2000, 1, 1, tzinfo=timezone.utc)
            patients = self.get_patients_updated_since(since)

            for i, patient in enumerate(patients):
                if on_progress:
                    on_progress("patients", i + 1, len(patients))

                if self.on_patient_sync:
                    try:
                        self.on_patient_sync(patient)
                        stats["patients_synced"] += 1
                    except Exception as e:
                        stats["errors"].append(f"Patient {patient.id}: {e}")

            self._last_patient_sync = datetime.now(timezone.utc)

        except Exception as e:
            stats["errors"].append(f"Patient sync failed: {e}")

        return stats


class EMRIntegrationAsync:
    """Async wrapper for EMR Integration."""

    def __init__(self, emr_db_path: Optional[Path] = None):
        self.emr = EMRIntegration(emr_db_path)

    async def get_patient(self, patient_id: str) -> Optional[EMRPatient]:
        """Async get patient."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.emr.get_patient(patient_id),
        )

    async def search_patients(
        self,
        query: str,
        limit: int = 20,
    ) -> list[EMRPatient]:
        """Async search patients."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.emr.search_patients(query, limit),
        )

    async def get_patient_visits(
        self,
        patient_id: str,
        limit: int = 10,
    ) -> list[EMRVisit]:
        """Async get patient visits."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.emr.get_patient_visits(patient_id, limit),
        )
