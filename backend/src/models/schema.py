from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Enum, JSON, Text, Boolean
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
    COMPATIBILITY_LAYER = "COMPATIBILITY_LAYER"
    FACADE_PATTERN = "FACADE_PATTERN"
    MIGRATION_LAYER = "MIGRATION_LAYER"
    WRAPPER_STRATEGY = "WRAPPER_STRATEGY"
    HUMAN_ESCALATION = "HUMAN_ESCALATION"

class NodeType(str, enum.Enum):
    MODULE = "MODULE"
    CLASS = "CLASS"
    FUNCTION = "FUNCTION"
    INTERFACE = "INTERFACE"

class EdgeType(str, enum.Enum):
    IMPORTS = "IMPORTS"
    CALLS = "CALLS"
    INHERITS = "INHERITS"
    IMPLEMENTS = "IMPLEMENTS"
    USES = "USES"

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
    # Graph-aware symbol fields
    symbol = Column(String, nullable=True)          # changed_symbol
    symbol_type = Column(String, nullable=True)     # MODULE | CLASS | FUNCTION | INTERFACE
    affected_functions = Column(JSON, nullable=True) # list of function names in blast radius
    affected_modules = Column(JSON, nullable=True)   # list of module names impacted
    critical_paths = Column(JSON, nullable=True)     # list of critical dependency paths
    impact_score = Column(Float, nullable=True)      # 0–100, derived by ImpactAnalyzer
    dependency_depth = Column(Integer, nullable=True) # max traversal depth of impact
    # Legacy / kept for backwards compat
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
    conflict_id = Column(Integer, ForeignKey("reconciliation_units.id"))
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

class DebateState(Base):
    __tablename__ = "debate_state"
    id = Column(Integer, primary_key=True, index=True)
    debate_id = Column(Integer, ForeignKey("debates.id"), unique=True)
    current_round = Column(Integer, default=0)
    current_position = Column(String, nullable=True)
    opponent_claims = Column(JSON, nullable=True)
    evidence_delta = Column(JSON, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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


# ──────────────────────────────────────────────────────────────────────────────
# Graph Intelligence Layer (graph_01.md — Stage 1)
# ──────────────────────────────────────────────────────────────────────────────

class GraphNode(Base):
    """Represents a code symbol (module, class, function, interface) in the dependency graph."""
    __tablename__ = "graph_nodes"
    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), index=True)
    node_name = Column(String, index=True)           # e.g. "decode_token"
    node_type = Column(Enum(NodeType))               # MODULE | CLASS | FUNCTION | INTERFACE
    file_path = Column(String)                       # e.g. "src/auth/jwt.py"
    node_metadata = Column(JSON, nullable=True)      # lineno, args, docstring, etc.


class GraphEdge(Base):
    """Represents a dependency relationship between two graph nodes."""
    __tablename__ = "graph_edges"
    id = Column(Integer, primary_key=True, index=True)
    source_node_id = Column(Integer, ForeignKey("graph_nodes.id"), index=True)
    target_node_id = Column(Integer, ForeignKey("graph_nodes.id"), index=True)
    edge_type = Column(Enum(EdgeType))               # IMPORTS | CALLS | INHERITS | IMPLEMENTS | USES


class ImpactAnalysis(Base):
    """Stores the computed impact analysis result for a reconciliation unit."""
    __tablename__ = "impact_analysis"
    id = Column(Integer, primary_key=True, index=True)
    reconciliation_unit_id = Column(Integer, ForeignKey("reconciliation_units.id"), unique=True)
    affected_functions = Column(JSON)                # list of function names
    affected_modules = Column(JSON)                  # list of module names
    dependency_depth = Column(Integer)               # BFS depth reached
    critical_paths = Column(JSON)                    # list of path lists
    impact_score = Column(Float)                     # 0.0 – 100.0
    created_at = Column(DateTime, default=datetime.utcnow)
