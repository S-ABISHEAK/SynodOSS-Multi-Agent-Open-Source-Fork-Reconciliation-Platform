"""
policy_analyzer.py

Post-debate service that analyzes agent messages to determine which enterprise
policies were impacted by the conflict and what business risks exist.

Runs deterministically after Round 4. No additional LLM call required.
Output is persisted as a PolicyImpactResult row.
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from src.models.schema import (
    PolicyImpactResult,
    RiskLevel,
    EnterprisePolicy,
    PolicyChunk,
    PolicyStatus,
)
from src.services.policy.policy_retriever import RetrievedPolicyChunk

logger = logging.getLogger(__name__)

# Risk escalation rules — if any CRITICAL policy is triggered, escalate
_CRITICAL_ESCALATION_THRESHOLD = 0.70
_HIGH_ESCALATION_THRESHOLD = 0.55


@dataclass
class PolicyImpactSummary:
    affected_policies: list[dict] = field(default_factory=list)  # {policy_id, name, category, reason}
    risk_level: RiskLevel = RiskLevel.LOW
    business_impact: str = ""
    escalation_needed: bool = False
    policy_impact_score: float = 0.0  # 0.0-1.0


class PolicyAnalyzer:
    def __init__(self, db: Session):
        self.db = db

    def analyze(
        self,
        debate_id: int,
        retrieved_chunks: list[RetrievedPolicyChunk],
        agent_messages: list[dict],
        arch_resolution: dict,
    ) -> PolicyImpactSummary:
        """
        Analyze which policies were impacted based on:
        1. Retrieved chunks (from retriever — similarity scores).
        2. Agent messages — check if agents explicitly referenced policy names.
        3. Architect resolution — does it involve HIGH-risk operations?

        Args:
            debate_id: The current debate ID.
            retrieved_chunks: Policy chunks retrieved for this conflict.
            agent_messages: List of agent response dicts from the debate rounds.
            arch_resolution: The Architect's final resolution dict.

        Returns:
            PolicyImpactSummary with risk assessment.
        """
        if not retrieved_chunks:
            return PolicyImpactSummary(
                risk_level=RiskLevel.LOW,
                business_impact="No enterprise policies matched this conflict.",
                escalation_needed=False,
                policy_impact_score=0.0,
            )

        # Step 1: Build affected policy list from retrieved chunks
        seen_policy_ids: set[int] = set()
        affected: list[dict] = []
        max_similarity = 0.0

        for chunk in retrieved_chunks:
            if chunk.policy_id in seen_policy_ids:
                continue
            seen_policy_ids.add(chunk.policy_id)
            if chunk.similarity_score > max_similarity:
                max_similarity = chunk.similarity_score

            # Check if any agent explicitly mentioned this policy
            agent_referenced = self._check_agents_referenced_policy(
                chunk.policy_name, agent_messages
            )

            affected.append({
                "policy_id": chunk.policy_id,
                "name": chunk.policy_name,
                "category": chunk.policy_category,
                "priority": chunk.policy_priority,
                "similarity_score": chunk.similarity_score,
                "reason": chunk.reason,
                "agent_referenced": agent_referenced,
            })

        # Step 2: Determine overall risk level
        priorities = {p["priority"] for p in affected}
        if "CRITICAL" in priorities or max_similarity >= _CRITICAL_ESCALATION_THRESHOLD:
            risk_level = RiskLevel.CRITICAL
        elif "HIGH" in priorities or max_similarity >= _HIGH_ESCALATION_THRESHOLD:
            risk_level = RiskLevel.HIGH
        elif "MEDIUM" in priorities:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        # Step 3: Determine escalation
        escalation_needed = risk_level in {RiskLevel.CRITICAL, RiskLevel.HIGH}

        # Step 4: Build business impact summary
        business_impact = self._build_business_impact_text(affected, risk_level, arch_resolution)

        # Step 5: Compute policy impact score (0.0-1.0)
        risk_weights = {RiskLevel.LOW: 0.1, RiskLevel.MEDIUM: 0.4, RiskLevel.HIGH: 0.7, RiskLevel.CRITICAL: 1.0}
        policy_impact_score = round(
            (risk_weights[risk_level] * 0.6) + (min(1.0, max_similarity) * 0.4),
            3
        )

        summary = PolicyImpactSummary(
            affected_policies=affected,
            risk_level=risk_level,
            business_impact=business_impact,
            escalation_needed=escalation_needed,
            policy_impact_score=policy_impact_score,
        )

        # Persist to DB
        self._persist(debate_id, summary)

        logger.info(
            f"[policy_analyzer] debate={debate_id} "
            f"affected_policies={len(affected)} risk={risk_level.value} "
            f"escalate={escalation_needed} score={policy_impact_score}"
        )
        return summary

    def _check_agents_referenced_policy(self, policy_name: str, messages: list[dict]) -> bool:
        """Check if any agent response text mentions the policy name."""
        name_lower = policy_name.lower()
        for msg in messages:
            # Check all text fields in the message
            for key in ["analysis", "rebuttal", "reason", "verification_summary"]:
                val = msg.get(key, "") or ""
                if name_lower in val.lower():
                    return True
            # Check referenced_policies list if present
            refs = msg.get("referenced_policies", [])
            if isinstance(refs, list) and policy_name in refs:
                return True
        return False

    def _build_business_impact_text(
        self,
        affected: list[dict],
        risk_level: RiskLevel,
        arch_resolution: dict,
    ) -> str:
        if not affected:
            return "No significant business impact detected."

        policy_names = ", ".join(p["name"] for p in affected[:3])
        resolution = arch_resolution.get("decision", arch_resolution.get("reason", ""))[:200]

        if risk_level == RiskLevel.CRITICAL:
            return (
                f"CRITICAL: This conflict directly impacts {len(affected)} enterprise policies "
                f"({policy_names}). The proposed resolution '{resolution}' requires immediate "
                f"senior engineering review before any code changes are applied."
            )
        elif risk_level == RiskLevel.HIGH:
            return (
                f"HIGH RISK: {len(affected)} enterprise policies affected ({policy_names}). "
                f"The resolution should be reviewed by a technical lead to ensure compliance."
            )
        elif risk_level == RiskLevel.MEDIUM:
            return (
                f"MEDIUM RISK: {len(affected)} policies ({policy_names}) are potentially affected. "
                f"Standard review process is recommended."
            )
        else:
            return (
                f"LOW RISK: {len(affected)} policies weakly matched ({policy_names}). "
                f"No critical business workflows appear impacted."
            )

    def _persist(self, debate_id: int, summary: PolicyImpactSummary):
        """Upsert the PolicyImpactResult row for this debate."""
        try:
            existing = self.db.query(PolicyImpactResult).filter_by(debate_id=debate_id).first()
            if existing:
                existing.affected_policies = summary.affected_policies
                existing.risk_level = summary.risk_level
                existing.business_impact = summary.business_impact
                existing.escalation_needed = summary.escalation_needed
                existing.policy_impact_score = summary.policy_impact_score
            else:
                row = PolicyImpactResult(
                    debate_id=debate_id,
                    affected_policies=summary.affected_policies,
                    risk_level=summary.risk_level,
                    business_impact=summary.business_impact,
                    escalation_needed=summary.escalation_needed,
                    policy_impact_score=summary.policy_impact_score,
                )
                self.db.add(row)
            self.db.commit()
        except Exception as e:
            logger.error(f"[policy_analyzer] Failed to persist PolicyImpactResult: {e}")
            self.db.rollback()
