from sqlalchemy.orm import Session
from src.models.schema import RepositoryScan, Conflict, DivergenceMetric, ScanStatus
from datetime import datetime

class PersistenceService:
    def __init__(self, db: Session):
        self.db = db

    def store_scan(self, upstream_repo_id: int, fork_repo_id: int) -> RepositoryScan:
        scan = RepositoryScan(upstream_repo_id=upstream_repo_id, fork_repo_id=fork_repo_id, status=ScanStatus.pending)
        self.db.add(scan)
        self.db.commit()
        self.db.refresh(scan)
        return scan

    def update_scan_status(self, scan_id: int, status: ScanStatus):
        scan = self.db.query(RepositoryScan).filter(RepositoryScan.id == scan_id).first()
        if scan:
            scan.status = status
            self.db.commit()
            
    def complete_scan(self, scan_id: int):
        scan = self.db.query(RepositoryScan).filter(RepositoryScan.id == scan_id).first()
        if scan:
            scan.status = ScanStatus.completed
            scan.completed_at = datetime.utcnow()
            self.db.commit()
            
    def store_metrics(self, scan_id: int, metrics_data: dict):
        metric = DivergenceMetric(
            scan_id=scan_id,
            upstream_commit_count=metrics_data.get("upstream_commit_count", 0),
            fork_commit_count=metrics_data.get("fork_commit_count", 0),
            commit_gap=metrics_data.get("commit_gap", 0),
            changed_files=metrics_data.get("changed_files", 0),
            deleted_files=metrics_data.get("deleted_files", 0),
            added_files=metrics_data.get("added_files", 0)
        )
        self.db.add(metric)
        self.db.commit()

    def store_conflicts(self, scan_id: int, conflicts_data: list):
        for c in conflicts_data:
            conflict = Conflict(
                scan_id=scan_id,
                file_path=c["file_path"],
                conflict_type=c["conflict_type"],
                severity=c["severity"],
                summary=c["summary"]
            )
            self.db.add(conflict)
        self.db.commit()

    def store_reconciliation_units(self, scan_id: int, units_data: list):
        from src.models.schema import ReconciliationUnit
        for u in units_data:
            unit = ReconciliationUnit(
                scan_id=scan_id,
                file_path=u.get("file_path", ""),
                diff_hunk=u.get("diff_hunk", ""),
                module=u.get("module"),
                symbol=u.get("symbol"),
                symbol_type=u.get("symbol_type"),
                impact_radius=u.get("impact_radius"),
                callers=u.get("callers"),
                dependencies=u.get("dependencies"),
                architectural_layer=u.get("architectural_layer"),
                upstream_commits=u.get("upstream_commits", []),
                fork_commits=u.get("fork_commits", []),
                complexity_score=u.get("complexity_score", 0.0),
                severity_score=u.get("severity_score", 0.0),
                status="pending_debate"
            )
            self.db.add(unit)
        self.db.commit()
