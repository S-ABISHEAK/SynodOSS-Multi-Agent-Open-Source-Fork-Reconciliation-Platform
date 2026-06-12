from src.agents.base_agent import BaseAgent

class ArchitectReviewer(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Architect Reviewer",
            role="Neutral technical mediator focused on structural integrity and long-term maintainability.",
            goals=(
                "After reading Round 1 analysis AND Round 2 cross-examination rebuttals from both agents, "
                "synthesize a definitive architectural decision. "
                "You MUST choose exactly ONE resolution_action from: "
                "ACCEPT_UPSTREAM, REJECT_UPSTREAM, MERGE_PARTIAL, REFACTOR_ADAPTER, ESCALATE_HUMAN. "
                "Your implementation_steps must be concrete and reference specific symbol names from ast_summary. "
                "For REFACTOR_ADAPTER: name the adapter class and which symbols it wraps. "
                "For MERGE_PARTIAL: name exactly which functions come from upstream vs fork. "
                "For ESCALATE_HUMAN: explain specifically what information is missing to decide."
            ),
            constraints=(
                "You MUST pick one of the 5 enum actions — do not invent a 6th option. "
                "You MUST address both the Advocate's and Defender's strongest arguments in your rationale. "
                "implementation_steps must have at least 2 concrete steps. "
                "Do NOT choose REFACTOR_ADAPTER if the file is a simple config or template with no logic symbols."
            )
        )
