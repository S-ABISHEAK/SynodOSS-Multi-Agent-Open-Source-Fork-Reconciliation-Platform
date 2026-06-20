from src.core.llm_provider import LLMProvider
from src.agents.upstream_advocate import UpstreamAdvocate
from src.agents.enterprise_defender import EnterpriseDefender
from src.agents.architect_reviewer import ArchitectReviewer
from src.agents.verification_judge import VerificationJudge
from src.agents.impact_analyst import ImpactAnalyst, ImpactReport
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
        self.impact_analyst = ImpactAnalyst()

    def _build_user_prompt(self, context: dict, previous_messages: list = None, extra_instruction: str = "", agent_type: str = "") -> str:
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

        # Agent-Specific Context Filtering (Problem 7)
        if agent_type in ["advocate", "impact_analyst"]:
            upstream_msgs = context.get("upstream_commit_messages", [])
            if upstream_msgs:
                parts.append(f"\n--- UPSTREAM COMMIT MESSAGES ---")
                for msg in upstream_msgs:
                    parts.append(msg)

        if agent_type in ["defender", "impact_analyst"]:
            fork_msgs = context.get("fork_commit_messages", [])
            if fork_msgs:
                parts.append(f"\n--- FORK COMMIT MESSAGES ---")
                for msg in fork_msgs:
                    parts.append(msg)

        if agent_type not in ["architect"]:
            parts.append(f"\n--- DIFF PREVIEW ---")
            parts.append(context.get("diff_preview", "(no diff)"))

        if agent_type in ["architect", "impact_analyst"]:
            # Architect ONLY gets the highly compressed JSON impact graph
            comp = context.get("compressed_context")
            if comp:
                parts.append(f"\n--- GRAPH IMPACT ANALYSIS (JSON) ---")
                parts.append(json.dumps(comp, indent=2))
        
        # Legacy/Text graph fallback for others
        elif agent_type not in ["judge"]:
            impact_score = context.get("impact_score", 0.0)
            affected_fns = context.get("affected_functions", [])
            affected_mods = context.get("affected_modules", [])
            critical_paths = context.get("critical_paths", [])
            dep_depth = context.get("dependency_depth", 0)
            changed_symbol = context.get("changed_symbol", "Unknown")

            if impact_score > 0 or affected_fns or critical_paths:
                parts.append(f"\n--- GRAPH IMPACT ANALYSIS ---")
                parts.append(f"Changed Symbol: {changed_symbol}")
                parts.append(f"Impact Score: {impact_score:.1f} / 100")
                parts.append(f"Dependency Depth: {dep_depth}")
                parts.append(f"Affected Functions ({len(affected_fns)}): {', '.join(affected_fns[:10])}")
                parts.append(f"Affected Modules ({len(affected_mods)}): {', '.join(affected_mods[:10])}")
                if critical_paths:
                    parts.append(f"Critical Paths:")
                    for path in critical_paths[:3]:
                        parts.append(f"  → {' → '.join(path)}")

        # Impact Analyst Report (injected if available)
        if context.get("impact_report"):
            parts.append(f"\n--- IMPACT ANALYST REPORT ---")
            report = context["impact_report"]
            parts.append(f"Risk Level: {report.get('risk_level', '?')}")
            parts.append(f"Blast Radius: {report.get('blast_radius_summary', '?')}")
            parts.append(f"Dependency Chain: {report.get('dependency_chain_summary', '?')}")
            key_risks = report.get("key_risks", [])
            if key_risks:
                parts.append(f"Key Risks:")
                for risk in key_risks:
                    parts.append(f"  - {risk}")

        upstream_content = context.get("upstream_file_content", "")
        if upstream_content and not upstream_content.startswith("(file not found"):
            parts.append(f"\n--- UPSTREAM FILE CONTENT ---")
            parts.append(upstream_content)

        fork_content = context.get("fork_file_content", "")
        if fork_content and not fork_content.startswith("(file not found"):
            parts.append(f"\n--- FORK FILE CONTENT ---")
            parts.append(fork_content)

        if previous_messages:
            parts.append(f"\n=== DEBATE HISTORY / STATE ===")
            for i, msg in enumerate(previous_messages):
                if isinstance(msg, dict) and "current_position" in msg:
                    # New Debate State structure
                    parts.append(f"Round Position: {msg.get('current_position')}")
                    parts.append(f"Opponent Claims: {json.dumps(msg.get('opponent_claims', {}), indent=2)}")
                else:
                    # Fallback or Judge parsing string
                    parts.append(f"\n{json.dumps(msg, indent=2)}")

        if extra_instruction:
            parts.append(f"\n=== YOUR TASK ===")
            parts.append(extra_instruction)

        if context.get("validation_report") and "Judge" in extra_instruction:
            parts.append(f"\n=== HARD EVIDENCE VALIDATION REPORT ===")
            parts.append("The EvidenceResolver service has strictly validated the claims made in this debate:")
            parts.append(context["validation_report"])
            parts.append("You MUST use this report to invalidate any HALLUCINATED or UNGROUNDED claims.")

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
        user_prompt = self._build_user_prompt(context, previous_messages, extra, agent_type=agent_type)

        logger.info(f"Prompting {agent_type} (context_len={len(user_prompt)})")
        response = self.llm.generate(system_prompt, user_prompt, schema=schema)
        response["agent_role"] = agent_type  # Ensure agent_role is always set
        return response

    def prompt_impact_analyst(self, context: dict) -> dict:
        """Pre-debate step (graph_02.md): Impact Analyst produces blast radius report."""
        system_prompt = self.impact_analyst.build_system_prompt()
        extra = (
            "Produce your ImpactReport now. Use the GRAPH IMPACT ANALYSIS section in the context. "
            "Derive risk_level from impact_score. Describe the dependency chain from critical_paths. "
            "List at least one key_risk per affected_function if the list is non-empty."
        )
        user_prompt = self._build_user_prompt(context, extra_instruction=extra, agent_type="impact_analyst")
        logger.info(f"Prompting impact_analyst (context_len={len(user_prompt)})")
        response = self.llm.generate(system_prompt, user_prompt, schema=ImpactReport)
        response["agent_role"] = "impact_analyst"
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
        user_prompt = self._build_user_prompt(context, [opposing_argument], extra, agent_type=agent_type)

        logger.info(f"Prompting {agent_type} rebuttal (context_len={len(user_prompt)})")
        response = self.llm.generate(system_prompt, user_prompt, schema=RebuttalSchema)
        response["agent_role"] = f"{agent_type}_rebuttal"
        return response
