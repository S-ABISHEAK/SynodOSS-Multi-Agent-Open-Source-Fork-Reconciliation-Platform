from src.core.database import SessionLocal
from src.models.schema import Debate, DebateMessage, ReconciliationUnit, DebateStatus
from src.orchestration.agent_manager import AgentManager
from src.orchestration.context_builder import ConflictContextBuilder
from src.orchestration.consensus_manager import ConsensusManager
import json
import logging
import traceback

logger = logging.getLogger(__name__)

CONFIDENCE_ESCALATION_THRESHOLD = 0.65


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
            # ── Round 0: Impact Analyst (non-voting, pre-debate) ─────────
            logger.info(f"[debate={debate.id}] Round 0: Impact Analyst pre-debate report")
            impact_report = self.agent_manager.prompt_impact_analyst(context)
            self._save_msg(db, debate.id, 0, "impact_analyst", impact_report)
            # Inject impact report into context so all agents can reference it
            context["impact_report"] = impact_report

            # ── Round 1: Independent Analysis ──────────────────────────
            logger.info(f"[debate={debate.id}] Round 1: Independent analysis")
            adv_res = self.agent_manager.prompt_agent("advocate", context)
            def_res = self.agent_manager.prompt_agent("defender", context)
            self._save_msg(db, debate.id, 1, "advocate", adv_res)
            self._save_msg(db, debate.id, 1, "defender", def_res)

            # ── Round 2: Cross-Examination ──────────────────────────────
            logger.info(f"[debate={debate.id}] Round 2: Cross-examination rebuttals")
            adv_rebuttal = self.agent_manager.prompt_rebuttal("advocate", context, def_res)
            def_rebuttal = self.agent_manager.prompt_rebuttal("defender", context, adv_res)
            self._save_msg(db, debate.id, 2, "advocate_rebuttal", adv_rebuttal)
            self._save_msg(db, debate.id, 2, "defender_rebuttal", def_rebuttal)

            # Full history for Architect
            full_history = [adv_res, def_res, adv_rebuttal, def_rebuttal]

            # ── Round 3: Architect Synthesis ────────────────────────────
            logger.info(f"[debate={debate.id}] Round 3: Architect synthesis")
            arch_res = self.agent_manager.prompt_agent("architect", context, full_history)
            self._save_msg(db, debate.id, 3, "architect", arch_res)
            full_history.append(arch_res)

            # ── Round 4: Verification Judge ────────────────────────────
            logger.info(f"[debate={debate.id}] Round 4: Verification judge (running EvidenceResolver)")
            from src.services.evidence_resolver import EvidenceResolver
            resolver = EvidenceResolver(self.context_builder.base_dir)
            fork_path = self.context_builder._get_repo_path(debate.conflict_id, "fork")

            validation_lines = resolver.build_validation_report(
                history=full_history,
                repo_path=fork_path,
                file_path=unit.file_path,
            )
            context["validation_report"] = "\n".join(validation_lines)
            judge_res = self.agent_manager.prompt_agent("judge", context, full_history)
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
            debate.status = DebateStatus.failed
            db.commit()

    # Keep old name as alias for backwards compat with routes.py
    def _run_4_round_loop(self, db, debate: Debate, unit: ReconciliationUnit):
        return self._run_debate_loop(db, debate, unit)
