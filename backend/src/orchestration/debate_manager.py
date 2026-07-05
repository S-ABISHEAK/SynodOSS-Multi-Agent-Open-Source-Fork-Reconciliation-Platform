from src.core.database import SessionLocal
from src.models.schema import Debate, DebateMessage, ReconciliationUnit, DebateStatus, DebateState
from src.orchestration.agent_manager import AgentManager
from src.orchestration.context_builder import ConflictContextBuilder, REPOS_BASE
from src.orchestration.consensus_manager import ConsensusManager
import json
import time
import logging
import traceback

logger = logging.getLogger(__name__)

CONFIDENCE_ESCALATION_THRESHOLD = 0.65
# Seconds to wait between LLM rounds — 1s is enough for llama-3.1-8b-instant
INTER_ROUND_DELAY = 1

# Max chars for each claim string stored in DebateState.opponent_claims
# to prevent token bloat in round 2 prompts.
_CLAIM_MAX_CHARS = 500


class DebateManager:
    def __init__(self):
        self.agent_manager = AgentManager()
        self.context_builder = ConflictContextBuilder()
        self.consensus_manager = ConsensusManager()

    def _save_msg(self, db, debate_id: int, round_num: int, agent: str, content: dict):
        """Persist a single agent message to the database."""
        # Normalize evidence_refs — always store as list of plain dicts
        raw_evidence = content.get("evidence_provided", [])
        if isinstance(raw_evidence, list) and raw_evidence:
            if isinstance(raw_evidence[0], dict):
                evidence_refs = raw_evidence
            else:
                evidence_refs = [{"description": str(e), "source": "unknown", "strength": 0.5} for e in raw_evidence]
        else:
            evidence_refs = []

        msg = DebateMessage(
            debate_id=debate_id,
            round=round_num,
            agent=agent,
            message=json.dumps(content, default=str),
            evidence_refs=evidence_refs,
        )
        db.add(msg)
        db.commit()
        logger.info(f"  [debate={debate_id}] Round {round_num} | agent={agent} | evidence={len(evidence_refs)}")

    def _run_debate_loop(self, db, debate: Debate, unit: ReconciliationUnit):
        """
        6-step adversarial debate loop:
          Round 1a — Advocate initial analysis
          Round 1b — Defender initial analysis
          Round 2a — Advocate rebuts Defender
          Round 2b — Defender rebuts Advocate
          Round 3  — Architect synthesizes and picks resolution_action
          Round 4  — Verification Judge audits all evidence
        """
        logger.info(f"[debate={debate.id}] Building rich context for unit={unit.id} ({unit.file_path})")
        context = self.context_builder.build_context(unit)

        ast_summary = context.get("ast_summary", {})
        logger.info(f"[debate={debate.id}] AST summary: {ast_summary.get('summary', 'none')}")

        try:
            # Initialize Debate State Machine — UPSERT pattern to survive restarts
            debate_state = db.query(DebateState).filter(DebateState.debate_id == debate.id).first()
            if debate_state is None:
                debate_state = DebateState(
                    debate_id=debate.id,
                    current_round=0,
                    current_position="Pending analysis",
                    opponent_claims={},
                    evidence_delta=[],
                )
                db.add(debate_state)
                db.commit()
            else:
                # Reset existing state for a fresh run
                debate_state.current_round = 0
                debate_state.current_position = "Pending analysis"
                debate_state.opponent_claims = {}
                debate_state.evidence_delta = []
                db.commit()

            # ── Round 0: Impact Analyst (non-voting, pre-debate) ─────────
            logger.info(f"[debate={debate.id}] Round 0: Impact Analyst pre-debate report")
            impact_report = self.agent_manager.prompt_impact_analyst(context)
            self._save_msg(db, debate.id, 0, "impact_analyst", impact_report)
            context["impact_report"] = impact_report
            time.sleep(INTER_ROUND_DELAY)

            # ── Round 1: Independent Analysis ──────────────────────────
            debate_state.current_round = 1
            db.commit()
            logger.info(f"[debate={debate.id}] Round 1: Independent analysis")
            adv_res = self.agent_manager.prompt_agent("advocate", context)
            time.sleep(INTER_ROUND_DELAY)
            def_res = self.agent_manager.prompt_agent("defender", context)
            self._save_msg(db, debate.id, 1, "advocate", adv_res)
            self._save_msg(db, debate.id, 1, "defender", def_res)

            # Update state with Round 1 claims (truncated to avoid token bloat in Round 2)
            def _cap(s):
                s = str(s)
                return s[:_CLAIM_MAX_CHARS] + "..." if len(s) > _CLAIM_MAX_CHARS else s

            debate_state.current_position = "Round 1 Complete"
            debate_state.opponent_claims = {
                "advocate_claims": _cap(adv_res.get("analysis", "")),
                "defender_claims": _cap(def_res.get("analysis", ""))
            }
            db.commit()
            time.sleep(INTER_ROUND_DELAY)

            # ── Round 2: Cross-Examination ──────────────────────────────
            debate_state.current_round = 2
            db.commit()
            logger.info(f"[debate={debate.id}] Round 2: Cross-examination rebuttals")
            # Pass only current_position & opponent_claims (not full history) to avoid token bloat
            adv_rebuttal = self.agent_manager.prompt_rebuttal(
                "advocate", context, debate_state.opponent_claims.get("defender_claims", "")
            )
            time.sleep(INTER_ROUND_DELAY)
            def_rebuttal = self.agent_manager.prompt_rebuttal(
                "defender", context, debate_state.opponent_claims.get("advocate_claims", "")
            )
            self._save_msg(db, debate.id, 2, "advocate_rebuttal", adv_rebuttal)
            self._save_msg(db, debate.id, 2, "defender_rebuttal", def_rebuttal)

            # Build a fresh dict so SQLAlchemy detects the mutation
            updated_claims = dict(debate_state.opponent_claims)
            updated_claims["advocate_rebuttal"] = adv_rebuttal.get("rebuttal", "")
            updated_claims["defender_rebuttal"] = def_rebuttal.get("rebuttal", "")
            debate_state.opponent_claims = updated_claims
            debate_state.current_position = "Round 2 Complete"
            db.commit()
            time.sleep(INTER_ROUND_DELAY)

            # ── Round 3: Architect Synthesis ────────────────────────────
            debate_state.current_round = 3
            db.commit()
            logger.info(f"[debate={debate.id}] Round 3: Architect synthesis")
            state_history = [
                {"current_position": debate_state.current_position, "opponent_claims": debate_state.opponent_claims}
            ]
            arch_res = self.agent_manager.prompt_agent("architect", context, state_history)
            self._save_msg(db, debate.id, 3, "architect", arch_res)
            time.sleep(INTER_ROUND_DELAY)

            # ── Round 4: Verification Judge ────────────────────────────
            debate_state.current_round = 4
            db.commit()
            logger.info(f"[debate={debate.id}] Round 4: Verification judge (running EvidenceResolver)")
            from src.services.evidence_resolver import EvidenceResolver
            resolver = EvidenceResolver(str(REPOS_BASE))
            fork_path = str(REPOS_BASE / str(unit.scan_id) / "fork")

            full_history = [adv_res, def_res, adv_rebuttal, def_rebuttal, arch_res]
            validation_lines = resolver.build_validation_report(
                history=full_history,
                repo_path=fork_path,
                file_path=unit.file_path,
            )
            context["validation_report"] = "\n".join(validation_lines)
            
            # Pass only the claims for judging, preventing full raw token bloat
            judge_state = [{"claims_to_verify": debate_state.opponent_claims, "architect_resolution": arch_res.get("reason") or arch_res.get("rationale")}]
            judge_res = self.agent_manager.prompt_agent("judge", context, judge_state)
            self._save_msg(db, debate.id, 4, "judge", judge_res)

            # ── Consensus ───────────────────────────────────────────────
            logger.info(f"[debate={debate.id}] Computing consensus")
            consensus = self.consensus_manager.summarize_debate(arch_res, judge_res)

            debate.architectural_proposal = consensus["proposal"]
            debate.resolution_action = consensus.get("resolution_action")
            debate.confidence = consensus["confidence"]
            debate.evidence_count = consensus["evidence_count"]
            debate.verification_score = consensus["verification_score"]
            debate.token_usage = consensus.get("token_usage", 0)

            # ── Policy Impact Analysis (EPACE) ──────────────────────────
            try:
                from src.services.policy.policy_analyzer import PolicyAnalyzer
                retrieved_chunks = context.get("_retrieved_policy_chunks", [])
                all_agent_msgs = [adv_res, def_res, adv_rebuttal, def_rebuttal, arch_res, judge_res]
                policy_analyzer = PolicyAnalyzer(db)
                policy_summary = policy_analyzer.analyze(
                    debate_id=debate.id,
                    retrieved_chunks=retrieved_chunks,
                    agent_messages=all_agent_msgs,
                    arch_resolution=arch_res,
                )
                logger.info(
                    f"[debate={debate.id}] Policy impact: risk={policy_summary.risk_level.value} "
                    f"escalate={policy_summary.escalation_needed} score={policy_summary.policy_impact_score}"
                )
                # HIGH/CRITICAL policy risk forces escalation regardless of confidence
                if policy_summary.escalation_needed and debate.confidence >= CONFIDENCE_ESCALATION_THRESHOLD:
                    logger.warning(
                        f"[debate={debate.id}] Policy risk '{policy_summary.risk_level.value}' "
                        f"forces escalation despite confidence={debate.confidence:.2f}"
                    )
                    debate.status = DebateStatus.escalated
                    db.commit()
                    return
            except Exception as policy_err:
                logger.warning(f"[debate={debate.id}] PolicyAnalyzer failed (non-fatal): {policy_err}")

            # Auto-escalate if confidence is below threshold
            if consensus["confidence"] < CONFIDENCE_ESCALATION_THRESHOLD:
                debate.status = DebateStatus.escalated
                logger.warning(
                    f"[debate={debate.id}] Confidence {consensus['confidence']:.2f} < "
                    f"{CONFIDENCE_ESCALATION_THRESHOLD} — escalating to human review"
                )
            else:
                debate.status = DebateStatus.completed

            db.commit()
            logger.info(f"[debate={debate.id}] Done — status={debate.status.value}, confidence={debate.confidence:.2f}")

        except Exception as e:
            logger.error(f"[debate={debate.id}] Debate loop failed: {e}")
            traceback.print_exc()
            try:
                db.rollback()
                debate.status = DebateStatus.failed
                db.commit()
            except Exception as commit_err:
                logger.error(f"[debate={debate.id}] Could not persist failed status: {commit_err}")

    # Keep old name as alias for backwards compat with routes.py
    def _run_4_round_loop(self, db, debate: Debate, unit: ReconciliationUnit):
        return self._run_debate_loop(db, debate, unit)
