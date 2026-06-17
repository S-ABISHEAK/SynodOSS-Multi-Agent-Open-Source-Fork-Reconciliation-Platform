"""
impact_analyst.py — Stage 2 (graph_02.md)

The Impact Analyst is a non-voting council member.

Responsibilities:
  - Calculate consequences of the changed symbol.
  - Produce an Impact Report with Blast Radius and Risk Score.
  - Does NOT vote. Does NOT debate.

The agent provides structured data to enrich the council's decision context.
"""

from src.agents.base_agent import BaseAgent
from pydantic import BaseModel, Field
from typing import List


class ImpactReport(BaseModel):
    """Structured output schema for the Impact Analyst."""
    agent_role: str = "Impact Analyst"
    changed_symbol: str = Field(..., description="The symbol (function, class, or module) that changed.")
    blast_radius_summary: str = Field(
        ...,
        description=(
            "Human-readable summary of what is at risk due to this change. "
            "Must reference the affected_functions and critical_paths from the graph context."
        ),
    )
    risk_level: str = Field(
        ...,
        description=(
            "Derived risk level: LOW (score < 30), MEDIUM (30–69), HIGH (70–89), CRITICAL (90+). "
            "Must match the impact_score provided in context."
        ),
    )
    dependency_chain_summary: str = Field(
        ...,
        description=(
            "Plain-English description of the critical dependency chain. "
            "Example: 'decode_token() → authenticate() → PaymentController → checkout_handler()'"
        ),
    )
    key_risks: List[str] = Field(
        default_factory=list,
        description=(
            "Specific risks identified from the dependency graph. "
            "Each item must reference a specific affected_function or module from the context."
        ),
    )
    confidence: float = Field(
        ...,
        description="Confidence in this impact assessment (0.0 to 1.0) based on graph data completeness.",
    )


class ImpactAnalyst(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Impact Analyst",
            role=(
                "Non-voting architectural consequence analyst. "
                "You analyze the structural blast radius of code changes using dependency graph data."
            ),
            goals=(
                "Given the graph-aware context (impact_score, affected_functions, affected_modules, "
                "critical_paths, dependency_depth), produce a structured ImpactReport. "
                "Your report must:\n"
                "1. Identify the risk_level derived from impact_score (LOW <30, MEDIUM 30-69, HIGH 70-89, CRITICAL 90+).\n"
                "2. Summarize the dependency chain from the critical_paths in plain English.\n"
                "3. List specific key_risks referencing named functions or modules from the context.\n"
                "4. Provide confidence based on how complete the graph data is."
            ),
            constraints=(
                "You do NOT vote on the resolution. You do NOT debate with other agents. "
                "You ONLY provide factual consequence analysis based on the graph data. "
                "Every claim in key_risks MUST reference a specific symbol name from affected_functions "
                "or affected_modules. Do not speculate about risks not visible in the graph context. "
                "If the graph context shows impact_score=0 or no affected functions, state that clearly."
            ),
        )

    def build_system_prompt(self) -> str:
        base = super().build_system_prompt()
        return base + """

ADDITIONAL CONTEXT FOR IMPACT ANALYST:
You will receive a graph-aware context with these additional fields:
- impact_score: float (0–100), computed from graph traversal
- affected_functions: list of function names reachable from the changed symbol
- affected_modules: list of module names impacted
- critical_paths: list of dependency chains (from changed symbol to leaf nodes)
- dependency_depth: integer representing how deep the blast radius propagates

Use these fields as the primary evidence for your ImpactReport.
Your report is injected into the Architect's context before Round 3 synthesis.
"""
