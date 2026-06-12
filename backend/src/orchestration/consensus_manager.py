import logging

logger = logging.getLogger(__name__)

# Confidence threshold below which we auto-escalate (same as debate_manager)
ESCALATION_THRESHOLD = 0.65


class ConsensusManager:
    def calculate_confidence(
        self,
        evidence_strength: float,
        evidence_coverage: float,
        argument_consistency: float,
        verification_score: float,
    ) -> float:
        """
        Weighted confidence formula:
          30% evidence_strength   — how strong was the evidence cited?
          25% evidence_coverage   — how many pieces of evidence were verified?
          20% argument_consistency — internal consistency of the debate
          25% verification_score  — Judge's penalty-adjusted score
        """
        confidence = (
            0.30 * evidence_strength
            + 0.25 * evidence_coverage
            + 0.20 * argument_consistency
            + 0.25 * verification_score
        )
        return round(min(max(confidence, 0.0), 1.0), 4)

    def summarize_debate(self, arch_response: dict, judge_verification: dict) -> dict:
        """
        Combine the Architect's decision and Judge's verification into a final consensus.
        Returns a dict with: proposal, resolution_action, confidence, evidence_count,
                             verification_score, token_usage.
        """
        # Extract architect fields
        resolution_action = arch_response.get("resolution_action")
        rationale = arch_response.get("rationale", "")
        implementation_steps = arch_response.get("implementation_steps", [])
        arch_confidence = arch_response.get("confidence", 0.5)
        arch_evidence = arch_response.get("evidence_provided", [])

        # Build human-readable proposal from resolution_action + rationale
        if resolution_action and rationale:
            steps_text = ""
            if implementation_steps:
                steps_text = "\n\nImplementation Steps:\n" + "\n".join(
                    f"  {i+1}. {step}" for i, step in enumerate(implementation_steps)
                )
            proposal = f"[{resolution_action}] {rationale}{steps_text}"
        else:
            # Fallback for old-format arch responses
            proposal = arch_response.get("proposed_action") or arch_response.get("analysis", "No consensus reached")

        # Extract judge fields
        penalty = float(judge_verification.get("adjusted_confidence_penalty", 0.0))
        verified_count = int(judge_verification.get("verified_evidence_count", 0))
        verification_score = round(max(0.0, 1.0 - penalty), 4)

        # Calculate evidence strength from architect's evidence (avg of strengths)
        if arch_evidence:
            strengths = [
                e.get("strength", 0.5) if isinstance(e, dict) else 0.5
                for e in arch_evidence
            ]
            evidence_strength = sum(strengths) / len(strengths)
        else:
            evidence_strength = arch_confidence * 0.6  # Degrade if no evidence

        # Coverage: what fraction of claimed evidence was verified?
        total_claimed = max(len(arch_evidence), 1)
        evidence_coverage = min(verified_count / total_claimed, 1.0)

        # Argument consistency: proxy from architect's own confidence
        argument_consistency = arch_confidence

        final_confidence = self.calculate_confidence(
            evidence_strength,
            evidence_coverage,
            argument_consistency,
            verification_score,
        )

        # Estimate token usage (rough calculation)
        token_usage = self._estimate_tokens(arch_response, judge_verification)

        logger.info(
            f"Consensus: action={resolution_action} confidence={final_confidence:.3f} "
            f"(strength={evidence_strength:.2f} coverage={evidence_coverage:.2f} "
            f"consistency={argument_consistency:.2f} v_score={verification_score:.2f})"
        )

        return {
            "proposal": proposal,
            "resolution_action": resolution_action,
            "confidence": final_confidence,
            "evidence_count": verified_count,
            "verification_score": verification_score,
            "token_usage": token_usage,
        }

    def _estimate_tokens(self, *responses) -> int:
        """Very rough token estimator: ~4 chars per token."""
        total_chars = sum(len(str(r)) for r in responses)
        return total_chars // 4
