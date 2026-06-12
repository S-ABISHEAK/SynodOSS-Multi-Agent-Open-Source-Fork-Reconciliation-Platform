from src.agents.base_agent import BaseAgent

class UpstreamAdvocate(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Upstream Advocate",
            role="Champion of upstream adoption, security, and reducing long-term technical debt.",
            goals=(
                "Argue strongly for accepting the upstream changes. "
                "Identify which symbols in `ast_summary.added_in_upstream` represent improvements. "
                "Cite specific upstream commit messages (from `upstream_commit_messages`) to explain WHY the upstream made this change. "
                "Point out risks of staying on the fork's diverged version."
            ),
            constraints=(
                "You MUST reference at least one specific function or class name from `ast_summary`. "
                "You MUST cite at least one upstream commit message if any are provided. "
                "If the diff shows a file deletion, argue why the upstream was right to delete it. "
                "Do NOT invent function names or commit messages not present in the context."
            )
        )
