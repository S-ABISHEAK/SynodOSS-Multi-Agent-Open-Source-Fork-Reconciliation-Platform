from src.workers.celery_app import celery_app
from src.core.database import SessionLocal
from src.services.repository_service import RepositoryService
from src.services.diff_analysis_service import DiffAnalysisService
from src.services.conflict_detection_service import ConflictDetectionService
from src.services.persistence_service import PersistenceService
from src.models.schema import ScanStatus, RepositoryScan
from src.services.graph_builder_service import GraphBuilderService
from src.services.impact_analyzer_service import ImpactAnalyzerService
from src.services.file_summary_service import FileSummaryService
from src.services.knowledge_invalidation_service import KnowledgeInvalidationService
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

        # ── Pre-scan: Invalidate any stale knowledge from a prior run ────
        invalidation_svc = KnowledgeInvalidationService(db)
        stale_count = invalidation_svc.invalidate_scan(scan_id)
        if stale_count:
            logger.info(f"Scan {scan_id}: Invalidated {stale_count} stale file summaries from prior run")

        # Step 1: Clone upstream
        logger.info(f"Scan {scan_id}: Cloning upstream {upstream_url}")
        upstream_path = repo_service.clone_repository(upstream_url, scan_id, "upstream")

        # Step 2: Clone fork
        logger.info(f"Scan {scan_id}: Cloning fork {fork_url}")
        fork_path = repo_service.clone_repository(fork_url, scan_id, "fork")

        # Step 2.5: Build Fork Graph (snapshot-versioned)
        scan = db.query(RepositoryScan).filter(RepositoryScan.id == scan_id).first()
        graph_builder = GraphBuilderService(db)
        logger.info(
            f"Scan {scan_id}: Building AST dependency graph for fork "
            f"(repo_id={scan.fork_repo_id})"
        )
        fork_graph = graph_builder.build_graph(scan.fork_repo_id, scan_id, fork_path)
        impact_analyzer = ImpactAnalyzerService(db)

        # Step 2.6: Generate file summaries for fork (knowledge layer — Phase 2)
        logger.info(f"Scan {scan_id}: Generating file summaries for fork")
        summary_svc = FileSummaryService(db)
        fork_summary_count = summary_svc.generate_summaries(
            scan_id=scan_id,
            repository_id=scan.fork_repo_id,
            repo_path=fork_path,
        )
        logger.info(f"Scan {scan_id}: Generated {fork_summary_count} fork file summaries")

        # Also generate summaries for upstream so context_builder can compare
        logger.info(f"Scan {scan_id}: Generating file summaries for upstream")
        upstream_summary_count = summary_svc.generate_summaries(
            scan_id=scan_id,
            repository_id=scan.upstream_repo_id,
            repo_path=upstream_path,
        )
        logger.info(f"Scan {scan_id}: Generated {upstream_summary_count} upstream file summaries")

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
            sev_score, sev_label = conflict_service.calculate_conflict_severity(
                ru["file_path"], ctype
            )
            comp_score = conflict_service.calculate_complexity(ru["diff_hunk"])

            ru["severity_score"] = sev_score
            ru["complexity_score"] = comp_score

            # Run Graph Impact Analysis if symbol is known
            symbol = ru.get("symbol", "Unknown")
            if symbol and symbol != "Unknown":
                logger.info(f"Scan {scan_id}: Analyzing graph impact for symbol '{symbol}'")
                impact_res = impact_analyzer.analyze(fork_graph, symbol, scan.fork_repo_id, scan_id)
                ru["affected_functions"] = impact_res.get("affected_functions", [])
                ru["affected_modules"] = impact_res.get("affected_modules", [])
                ru["dependency_depth"] = impact_res.get("dependency_depth", 0)
                ru["critical_paths"] = impact_res.get("critical_paths", [])
                ru["impact_score"] = impact_res.get("impact_score", 0.0)

            processed_units.append(ru)

        persistence.store_reconciliation_units(scan_id, processed_units)

        # Complete scan
        persistence.complete_scan(scan_id)
        logger.info(f"Scan {scan_id}: Completed successfully")

        # ── Post-scan: Prune old snapshots (keep last 3 per repo) ────────
        try:
            fork_pruned = invalidation_svc.cleanup_old_snapshots(
                scan.fork_repo_id, keep_last_n=3
            )
            upstream_pruned = invalidation_svc.cleanup_old_snapshots(
                scan.upstream_repo_id, keep_last_n=3
            )
            logger.info(
                f"Scan {scan_id}: Pruned old snapshots — "
                f"fork={fork_pruned} upstream={upstream_pruned}"
            )
        except Exception as prune_err:
            # Pruning failure must never fail the scan itself
            logger.warning(f"Scan {scan_id}: Snapshot pruning failed (non-fatal): {prune_err}")

    except Exception as e:
        logger.error(f"Scan {scan_id}: Failed with error: {str(e)}")
        persistence.db.rollback()
        persistence.update_scan_status(scan_id, ScanStatus.failed)
    finally:
        db.close()
