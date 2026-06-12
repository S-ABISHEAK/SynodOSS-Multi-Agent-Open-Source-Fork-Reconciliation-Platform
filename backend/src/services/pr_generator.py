class PRGenerator:
    def generate_pr(self, conflict: dict, adr: dict, patch: dict) -> dict:
        """
        Generates GitHub-ready Pull Request markdown incorporating the conflict breakdown and decision log.
        """
        title = f"Reconciliation: {conflict.get('file_path', 'File')} - {conflict.get('conflict_type', 'Conflict')}"
        
        summary = f"""### Conflict Breakdown
{conflict.get('summary', 'Unknown Conflict')}

### Decision Log
{adr.get('architect_decision', 'Unknown Decision')}

### Verification Results
Applicability Passed: {patch.get('applicability_passed', False)}
Strategy: {patch.get('metadata', {}).get('strategy', 'Unknown')}
Files Modified: {patch.get('metadata', {}).get('files_modified', 0)}
Lines Added: +{patch.get('metadata', {}).get('lines_added', 0)}
Lines Removed: -{patch.get('metadata', {}).get('lines_removed', 0)}
"""
        
        return {
            "title": title,
            "summary": summary
        }
