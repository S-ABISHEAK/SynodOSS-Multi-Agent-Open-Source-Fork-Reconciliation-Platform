class ReconciliationEngine:
    def generate_plan(self, conflict: dict, consensus_decision: dict) -> dict:
        """
        Maps consensus decisions to a structured reconciliation plan.
        Returns a structured plan ready for Patch Generation.
        """
        strategy = consensus_decision.get("strategy", "PRESERVE_FORK")
        target_content = consensus_decision.get("target_content", "")
        replacement_content = consensus_decision.get("replacement_content", "")
        
        return {
            "strategy": strategy,
            "target_file": conflict.get("file_path", "unknown"),
            "target_content": target_content,
            "replacement_content": replacement_content
        }
