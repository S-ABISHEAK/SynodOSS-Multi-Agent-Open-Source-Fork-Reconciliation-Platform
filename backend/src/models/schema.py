from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Enum, JSON
import enum
from src.models.base import Base

class RepositoryType(str, enum.Enum):
    upstream = "upstream"
    fork = "fork"

class ScanStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"

class ConflictType(str, enum.Enum):
    dependency = "dependency"
    api = "api"
    architecture = "architecture"
    configuration = "configuration"
    security = "security"
    performance = "performance"

class ConflictSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class DebateStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"
    escalated = "escalated"

class RoundType(str, enum.Enum):
    analysis = "analysis"
    cross_examination = "cross_examination"
    review = "review"

class ArchitecturalProposalType(str, enum.Enum):
    ADAPTER_PATTERN = "ADAPTER_PATTERN"
    FACADE_PATTERN = "FACADE_PATTERN"
    COMPATIBILITY_LAYER = "COMPATIBILITY_LAYER"
    MIGRATION_LAYER = "MIGRATION_LAYER"
    WRAPPER_STRATEGY = "WRAPPER_STRATEGY"
    MANUAL_ESCALATION = "MANUAL_ESCALATION"

class Repository(Base):
    __tablename__ = "repositories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    url = Column(String)
    type = Column(Enum(RepositoryType))
    default_branch = Column(String)
    fingerprint = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class RepositoryScan(Base):
    __tablename__ = "repository_scans"
    id = Column(Integer, primary_key=True, index=True)
    upstream_repo_id = Column(Integer, ForeignKey("repositories.id"))
    fork_repo_id = Column(Integer, ForeignKey("repositories.id"))
    status = Column(Enum(ScanStatus), default=ScanStatus.pending)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
class Commit(Base):
    __tablename__ = "commits"
    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"))
    commit_hash = Column(String, index=True)
    author = Column(String)
    message = Column(String)
    timestamp = Column(DateTime)

class File(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"))
    file_path = Column(String)
    language = Column(String)
    file_hash = Column(String)

class Conflict(Base):
    __tablename__ = "conflicts"
    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("repository_scans.id"))
    file_path = Column(String)
    conflict_type = Column(Enum(ConflictType))
    severity = Column(Enum(ConflictSeverity))
    summary = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class DivergenceMetric(Base):
    __tablename__ = "divergence_metrics"
    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("repository_scans.id"))
    upstream_commit_count = Column(Integer)
    fork_commit_count = Column(Integer)
    commit_gap = Column(Integer)
    changed_files = Column(Integer)
    deleted_files = Column(Integer)
    added_files = Column(Integer)

class ReconciliationUnit(Base):
    __tablename__ = "reconciliation_units"
    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("repository_scans.id"))
    file_path = Column(String)
    diff_hunk = Column(String)
    module = Column(String, nullable=True)
    symbol = Column(String, nullable=True)
    symbol_type = Column(String, nullable=True)
    impact_radius = Column(Integer, nullable=True)
    callers = Column(JSON, nullable=True)
    dependencies = Column(JSON, nullable=True)
    architectural_layer = Column(String, nullable=True)
    upstream_commits = Column(JSON)
    fork_commits = Column(JSON)
    complexity_score = Column(Float)
    severity_score = Column(Float)
    status = Column(String)
    
class Debate(Base):
    __tablename__ = "debates"
    id = Column(Integer, primary_key=True, index=True)
    conflict_id = Column(Integer, ForeignKey("conflicts.id"))
    status = Column(Enum(DebateStatus), default=DebateStatus.pending)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Debate outcome columns
    architectural_proposal = Column(String, nullable=True)
    resolution_action = Column(String, nullable=True)   # ACCEPT_UPSTREAM | REJECT_UPSTREAM | MERGE_PARTIAL | REFACTOR_ADAPTER | ESCALATE_HUMAN
    consensus_score = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    evidence_count = Column(Integer, nullable=True)
    verification_score = Column(Float, nullable=True)
    token_usage = Column(Integer, nullable=True)

class DebateRound(Base):
    __tablename__ = "debate_rounds"
    id = Column(Integer, primary_key=True, index=True)
    debate_id = Column(Integer, ForeignKey("debates.id"))
    round_number = Column(Integer)
    round_type = Column(Enum(RoundType))

class AgentResponse(Base):
    __tablename__ = "agent_responses"
    id = Column(Integer, primary_key=True, index=True)
    debate_id = Column(Integer, ForeignKey("debates.id"))
    round_id = Column(Integer, ForeignKey("debate_rounds.id"))
    agent_name = Column(String)
    response = Column(JSON)
    confidence = Column(Float)
    evidence_count = Column(Integer)

class DebateMessage(Base):
    __tablename__ = "debate_messages"
    id = Column(Integer, primary_key=True, index=True)
    debate_id = Column(Integer, ForeignKey("debates.id"))
    round = Column(Integer)
    agent = Column(String)
    message = Column(String)
    evidence_refs = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)

class PullRequest(Base):
    __tablename__ = "pull_requests"
    id = Column(Integer, primary_key=True, index=True)
    conflict_id = Column(Integer, ForeignKey("conflicts.id"))
    title = Column(String)
    summary = Column(String)
    patch_content = Column(String)
    patch_metadata = Column(JSON)
    status = Column(String)
    trust_score = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class DecisionRecord(Base):
    __tablename__ = "decision_records"
    id = Column(Integer, primary_key=True, index=True)
    conflict_id = Column(Integer, ForeignKey("conflicts.id"))
    architect_decision = Column(String)
    evidence = Column(JSON)
    verification_result = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
