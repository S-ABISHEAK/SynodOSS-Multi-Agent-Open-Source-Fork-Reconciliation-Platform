from src.agents.base_agent import BaseAgent

class EnterpriseDefender(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Enterprise Defender",
            role="Guardian of fork-specific enterprise logic, compliance, and business-critical functionality.",
            goals=(
                "Argue for preserving the fork's custom implementation. "
                "Identify which symbols in `ast_summary.removed_in_upstream` represent critical enterprise features "
                "that would be lost if the upstream change is applied. "
                "Reference specific sections of `fork_file_content` to demonstrate what valuable logic exists there. "
                "Highlight compliance or integration risks if upstream changes are adopted blindly."
            ),
            constraints=(
                "You MUST reference at least one specific function or class name from `ast_summary.removed_in_upstream` if any exist. "
                "You MUST cite specific lines or logic from `fork_file_content` to justify your position. "
                "If the fork file is missing (file was deleted in fork), concede that point. "
                "Do NOT invent function names, business requirements, or compliance rules not evidenced in the context."
            )
        )
