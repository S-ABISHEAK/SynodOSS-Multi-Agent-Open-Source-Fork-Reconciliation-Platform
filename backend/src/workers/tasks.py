from src.workers.celery_app import celery_app
from src.core.database import SessionLocal
from src.services.repository_service import RepositoryService
from src.services.diff_analysis_service import DiffAnalysisService
from src.services.conflict_detection_service import ConflictDetectionService
from src.services.persistence_service import PersistenceService
from src.models.schema import ScanStatus
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def run_repository_scan(self, scan_id: int, upstream_url: str, fork_url: str):
    db = SessionLocal()
    persistence = PersistenceService(db)
    
    try:
        persistence.update_scan_status(scan_id, ScanStatus.running)
        
        repo_service = RepositoryService()
        diff_service = DiffAnalysisService()
        conflict_service = ConflictDetectionService()
        
        # Step 1: Clone upstream
        logger.info(f"Scan {scan_id}: Cloning upstream {upstream_url}")
        upstream_path = repo_service.clone_repository(upstream_url, scan_id, "upstream")
        
        # Step 2: Clone fork
        logger.info(f"Scan {scan_id}: Cloning fork {fork_url}")
        fork_path = repo_service.clone_repository(fork_url, scan_id, "fork")
        
        # Calculate Divergence
        logger.info(f"Scan {scan_id}: Calculating divergence metrics")
        metrics = diff_service.calculate_divergence(scan_id)
        persistence.store_metrics(scan_id, metrics)
        
        # Detect Conflicts
        logger.info(f"Scan {scan_id}: Detecting conflicts")
        conflicts = conflict_service.detect_conflicts(metrics.get("files_list", []))
        persistence.store_conflicts(scan_id, conflicts)
        
        # Extract Reconciliation Units
        logger.info(f"Scan {scan_id}: Extracting Reconciliation Units")
        raw_units = diff_service.extract_reconciliation_units(upstream_path, fork_path)
        
        processed_units = []
        for ru in raw_units:
            ctype = conflict_service.categorize_conflicts(ru["file_path"])
            sev_score, sev_label = conflict_service.calculate_conflict_severity(ru["file_path"], ctype)
            comp_score = conflict_service.calculate_complexity(ru["diff_hunk"])
            
            ru["severity_score"] = sev_score
            ru["complexity_score"] = comp_score
            processed_units.append(ru)
            
        persistence.store_reconciliation_units(scan_id, processed_units)
        
        # Complete
        persistence.complete_scan(scan_id)
        logger.info(f"Scan {scan_id}: Completed successfully")
        
    except Exception as e:
        logger.error(f"Scan {scan_id}: Failed with error: {str(e)}")
        persistence.update_scan_status(scan_id, ScanStatus.failed)
    finally:
        db.close()
