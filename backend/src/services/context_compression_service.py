import logging
from typing import Dict, Any
from src.models.schema import ReconciliationUnit
from src.orchestration.context_builder import ConflictContextBuilder

logger = logging.getLogger(__name__)

class ContextCompressionService:
    """
    Compresses raw repository files into a strict JSON-like context payload
    to avoid token explosion.
    Pipeline: Repository -> AST Extraction -> Symbol Extraction -> Dependency Analysis -> Impact Analysis -> Compressed Context
    """
    def __init__(self):
        # We reuse ContextBuilder's AST extraction internally, but we don't return raw files.
        self.context_builder = ConflictContextBuilder()

    def compress(self, unit: ReconciliationUnit) -> Dict[str, Any]:
        """
        Takes a ReconciliationUnit and extracts only the compressed graph/impact schema.
        Never sends raw file contents unless explicitly bypassed.
        """
        scan_id = unit.scan_id
        file_path = unit.file_path
        
        upstream_content = self.context_builder._read_file(scan_id, "upstream", file_path)
        fork_content = self.context_builder._read_file(scan_id, "fork", file_path)
        
        ast_summary = self.context_builder._build_ast_summary(upstream_content, fork_content, file_path)
        
        # Infer changed signature
        symbol = unit.symbol or "unknown"
        changed_signature = symbol in ast_summary.get("modified", [])
        
        # Determine security impact (naive heuristic for demo)
        security_impact = "LOW"
        if any(sec_keyword in file_path.lower() for sec_keyword in ["auth", "jwt", "crypto", "security"]):
            security_impact = "HIGH"
            
        callers_count = len(unit.callers) if unit.callers else 0

        # Construct required output schema
        compressed_context = {
            "symbol": symbol,
            "type": unit.symbol_type.lower() if unit.symbol_type else "function",
            "callers": callers_count,
            "affected_modules": len(unit.affected_modules) if unit.affected_modules else 0,
            "dependency_depth": unit.dependency_depth or 0,
            "changed_signature": changed_signature,
            "security_impact": security_impact,
            # Extra architect input fields (Problem 5: Architect Input)
            "affected_functions": len(unit.affected_functions) if unit.affected_functions else 0,
            "impact_score": unit.impact_score or 0.0
        }
        
        return compressed_context
