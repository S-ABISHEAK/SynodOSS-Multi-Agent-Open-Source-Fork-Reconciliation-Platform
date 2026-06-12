from src.core.llm_provider import LLMProvider
from src.agents.upstream_advocate import UpstreamAdvocate
from src.agents.enterprise_defender import EnterpriseDefender
from src.agents.architect_reviewer import ArchitectReviewer
from src.agents.verification_judge import VerificationJudge
from src.agents.base_agent import (
    AgentResponseSchema,
    ArchitectResolutionSchema,
    RebuttalSchema,
    VerificationResponseSchema,
)
import json
import logging

logger = logging.getLogger(__name__)


class AgentManager:
    def __init__(self):
        self.llm = LLMProvider()
        self.advocate = UpstreamAdvocate()
        self.defender = EnterpriseDefender()
        self.architect = ArchitectReviewer()
        self.judge = VerificationJudge()

    def _build_user_prompt(self, context: dict, previous_messages: list = None, extra_instruction: str = "") -> str:
        """Build a structured, readable user prompt from the rich context dict."""
        parts = []

        parts.append("=== CONFLICT CONTEXT ===")
        parts.append(f"File: {context.get('file_path', 'Unknown')}")
        parts.append(f"Complexity Score: {context.get('complexity_score', 0)}")

        ast_summary = context.get("ast_summary", {})
        if ast_summary:
            parts.append(f"\n--- AST STRUCTURAL SUMMARY ---")
            parts.append(f"Language: {ast_summary.get('language', 'unknown')}")
            parts.append(f"Summary: {ast_summary.get('summary', '')}")
            added = ast_summary.get("added_in_upstream", [])
            removed = ast_summary.get("removed_in_upstream", [])
            modified = ast_summary.get("modified", [])
            if added:
                parts.append(f"Upstream ADDED symbols: {', '.join(added)}")
            if removed:
                parts.append(f"Upstream REMOVED symbols (still in fork): {', '.join(removed)}")
            if modified:
                parts.append(f"MODIFIED symbols: {', '.join(modified)}")

        upstream_msgs = context.get("upstream_commit_messages", [])
        if upstream_msgs:
            parts.append(f"\n--- UPSTREAM COMMIT MESSAGES ---")
            for msg in upstream_msgs:
                parts.append(msg)

        fork_msgs = context.get("fork_commit_messages", [])
        if fork_msgs:
            parts.append(f"\n--- FORK COMMIT MESSAGES ---")
            for msg in fork_msgs:
                parts.append(msg)

        parts.append(f"\n--- DIFF PREVIEW ---")
        parts.append(context.get("diff_preview", "(no diff)"))

        upstream_content = context.get("upstream_file_content", "")
        if upstream_content and not upstream_content.startswith("(file not found"):
            parts.append(f"\n--- UPSTREAM FILE CONTENT ---")
            parts.append(upstream_content)

        fork_content = context.get("fork_file_content", "")
        if fork_content and not fork_content.startswith("(file not found"):
            parts.append(f"\n--- FORK FILE CONTENT ---")
            parts.append(fork_content)

        if previous_messages:
            parts.append(f"\n=== DEBATE HISTORY ===")
            for i, msg in enumerate(previous_messages):
                role = msg.get("agent_role", msg.get("role", f"Agent {i+1}"))
                parts.append(f"\n[{role}]")
                # Show key fields
                for key in ["analysis", "rebuttal", "rationale", "verification_summary"]:
                    if msg.get(key):
                        parts.append(f"{key.upper()}: {msg[key]}")
                evidence = msg.get("evidence_provided", [])
                if evidence:
                    parts.append(f"EVIDENCE ({len(evidence)} items):")
                    for ev in evidence[:3]:  # Cap at 3 to avoid prompt explosion
                        ev_str = ev if isinstance(ev, str) else f"[{ev.get('source','?')}] {ev.get('description','?')} (strength={ev.get('strength',0)})"
                        parts.append(f"  - {ev_str}")

        if extra_instruction:
            parts.append(f"\n=== YOUR TASK ===")
            parts.append(extra_instruction)

        return "\n".join(parts)

    def prompt_agent(self, agent_type: str, context: dict, previous_messages: list = None) -> dict:
        """Standard analysis round (Round 1 / Round 3 Architect)."""
        if agent_type == "advocate":
            agent = self.advocate
            schema = AgentResponseSchema
            extra = "Provide your initial analysis arguing for upstream adoption. Cite specific symbols and commit messages."
        elif agent_type == "defender":
            agent = self.defender
            schema = AgentResponseSchema
            extra = "Provide your initial analysis arguing for preserving the fork. Cite specific symbols from the fork file."
        elif agent_type == "architect":
            agent = self.architect
            schema = ArchitectResolutionSchema
            extra = (
                "You have read the full debate. Now provide your architectural resolution. "
                "Choose exactly ONE resolution_action from the enum. "
                "List concrete implementation_steps referencing specific symbol names."
            )
        elif agent_type == "judge":
            agent = self.judge
            schema = VerificationResponseSchema
            extra = (
                "Audit all evidence from all agents. Verify line numbers and symbol names against the provided context. "
                "Invalidate any claim that references symbols or line numbers not present in the context."
            )
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")

        system_prompt = agent.build_system_prompt()
        user_prompt = self._build_user_prompt(context, previous_messages, extra)

        logger.info(f"Prompting {agent_type} (context_len={len(user_prompt)})")
        response = self.llm.generate(system_prompt, user_prompt, schema=schema)
        response["agent_role"] = agent_type  # Ensure agent_role is always set
        return response

    def prompt_rebuttal(self, agent_type: str, context: dict, opposing_argument: dict) -> dict:
        """Cross-examination round (Round 2): agent rebuts opposing agent's argument."""
        if agent_type == "advocate":
            agent = self.advocate
            extra = (
                "You are now in Round 2: Cross-Examination. "
                "Read the Defender's argument carefully and write a focused rebuttal. "
                "Address their strongest points. Concede any valid points. Contest claims that lack grounding."
            )
        elif agent_type == "defender":
            agent = self.defender
            extra = (
                "You are now in Round 2: Cross-Examination. "
                "Read the Advocate's argument carefully and write a focused rebuttal. "
                "Address their strongest points. Concede any valid points. Contest claims that lack grounding."
            )
        else:
            raise ValueError(f"Rebuttal only supported for advocate/defender, got: {agent_type}")

        system_prompt = agent.build_system_prompt()
        user_prompt = self._build_user_prompt(context, [opposing_argument], extra)

        logger.info(f"Prompting {agent_type} rebuttal (context_len={len(user_prompt)})")
        response = self.llm.generate(system_prompt, user_prompt, schema=RebuttalSchema)
        response["agent_role"] = f"{agent_type}_rebuttal"
        return response
