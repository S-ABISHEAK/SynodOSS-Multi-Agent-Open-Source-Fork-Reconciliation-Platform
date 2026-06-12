import json

class ADRGenerator:
    def generate_adr(self, conflict: dict, consensus: dict, verification: dict) -> dict:
        """
        Generates an Architecture Decision Record (ADR).
        """
        problem = conflict.get("summary", "Unknown Conflict")
        decision = consensus.get("strategy", "Unknown Strategy")
        
        adr_content = f"""# Architecture Decision Record
        
## Problem
{problem}

## Decision
{decision}

## Tradeoffs
{consensus.get("tradeoffs", "Not specified.")}

## Evidence
{json.dumps(consensus.get("evidence", []), indent=2)}

## Verification Result
Trust Score: {verification.get("trust_score", {}).get("final_trust", "N/A")}
Applicability Passed: {verification.get("applicability_passed", False)}
"""
        return {
            "architect_decision": decision,
            "evidence": consensus.get("evidence", []),
            "verification_result": verification,
            "content": adr_content
        }
