from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from enum import Enum

# ──────────────────────────────────────────────
# Resolution Action Enum (Architect must pick one)
# ──────────────────────────────────────────────
class ResolutionAction(str, Enum):
    ACCEPT_UPSTREAM   = "ACCEPT_UPSTREAM"    # Take upstream as-is
    REJECT_UPSTREAM   = "REJECT_UPSTREAM"    # Keep fork as-is
    MERGE_PARTIAL     = "MERGE_PARTIAL"      # Merge specific sections from each
    REFACTOR_ADAPTER  = "REFACTOR_ADAPTER"   # Build an adapter/facade layer
    ESCALATE_HUMAN    = "ESCALATE_HUMAN"     # Too complex, needs human review


# ──────────────────────────────────────────────
# Evidence Model — now requires line citations
# ──────────────────────────────────────────────
class Evidence(BaseModel):
    file: str = Field(
        ...,
        description="The filename where the evidence is located."
    )
    symbol: Optional[str] = Field(
        None,
        description="The specific function or class name this evidence pertains to."
    )
    line_start: Optional[int] = Field(
        None,
        description="Starting line number."
    )
    line_end: Optional[int] = Field(
        None,
        description="Ending line number."
    )
    commit: Optional[str] = Field(
        None,
        description="The commit hash if referring to a specific git commit."
    )
    verified: bool = Field(
        False,
        description="Must be True if verified. Unverified evidence will be automatically rejected."
    )
    description: str = Field(
        ...,
        description="What the evidence shows."
    )


# ──────────────────────────────────────────────
# Standard Agent Response (Advocate, Defender, Architect initial analysis)
# ──────────────────────────────────────────────
class AgentResponseSchema(BaseModel):
    agent_role: str = Field(..., description="The role of the agent responding")
    analysis: str = Field(
        ...,
        description="Your argument. Must reference specific symbol names from ast_summary or line numbers from the diff."
    )
    evidence_provided: List[Evidence] = Field(
        default_factory=list,
        description="Concrete evidence supporting your argument. Each item must reference source material."
    )
    proposed_action: Optional[str] = Field(
        None,
        description="Brief description of what you propose should happen"
    )
    confidence: float = Field(
        ...,
        description="Confidence in your argument (0.0 to 1.0)"
    )


# ──────────────────────────────────────────────
# Architect Resolution Schema — enforced enum action
# ──────────────────────────────────────────────
class ArchitectResolutionSchema(BaseModel):
    agent_role: str = "Architect Reviewer"
    decision: Literal[
        "ADAPTER_PATTERN", 
        "COMPATIBILITY_LAYER", 
        "FACADE_PATTERN", 
        "MIGRATION_LAYER", 
        "WRAPPER_STRATEGY", 
        "HUMAN_ESCALATION",
    ] = Field(description="Strict enum representing the structural architecture decision.")
    reason: str = Field(
        ...,
        description="Why you chose this decision. Must reference specific symbols and arguments from the debate."
    )
    migration_cost: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        ...,
        description="Estimated migration cost/effort."
    )
    affected_modules: int = Field(
        ...,
        description="Number of modules affected by this architectural decision."
    )
    implementation_steps: List[str] = Field(
        default_factory=list,
        description="Concrete, ordered steps to execute the resolution."
    )
    evidence_provided: List[Evidence] = Field(
        default_factory=list,
        description="Evidence grounding your architectural decision."
    )


# ──────────────────────────────────────────────
# Cross-Examination Rebuttal Schema (Round 2)
# ──────────────────────────────────────────────
class RebuttalSchema(BaseModel):
    agent_role: str = Field(..., description="The role of the agent writing the rebuttal")
    rebuttal: str = Field(
        ...,
        description="Your direct rebuttal to the opposing agent's argument. Must address specific points they made."
    )
    conceded_points: List[str] = Field(
        default_factory=list,
        description="Points from the opposing argument you concede are valid."
    )
    contested_points: List[str] = Field(
        default_factory=list,
        description="Points from the opposing argument you dispute, with reasons."
    )
    evidence_provided: List[Evidence] = Field(
        default_factory=list,
        description="New evidence supporting your rebuttal."
    )
    confidence: float = Field(..., description="Updated confidence after hearing the opposing argument (0.0 to 1.0)")


# ──────────────────────────────────────────────
# Verification Judge Response
# ──────────────────────────────────────────────
class VerificationResponseSchema(BaseModel):
    agent_role: str = "Verification Judge"
    verification_summary: str = Field(
        ...,
        description="Summary of what evidence was verifiable vs. speculative."
    )
    invalidated_claims: List[str] = Field(
        default_factory=list,
        description="Claims that referenced non-existent line numbers or hallucinated symbol names."
    )
    verified_evidence_count: int = Field(
        ...,
        description="Number of evidence items that were directly verifiable in the provided code context."
    )
    adjusted_confidence_penalty: float = Field(
        ...,
        description="Penalty to subtract from consensus confidence (0.0 = no penalty, 1.0 = full invalidation)."
    )
    # Stage 2 additions — Trust Score components (graph_02.md)
    evidence_validity_score: float = Field(
        default=0.0,
        description="Ratio of valid evidence to total evidence (0.0–1.0). Derived from validation_report."
    )
    graph_consistency_score: float = Field(
        default=0.0,
        description=(
            "Score (0.0–1.0) reflecting how well agent claims align with the dependency graph. "
            "1.0 = all architectural claims are consistent with graph edges. "
            "0.0 = claims contradict or ignore graph data entirely."
        )
    )
    agent_agreement_score: float = Field(
        default=0.0,
        description=(
            "Score (0.0–1.0) measuring alignment between Advocate and Defender conclusions. "
            "Derived from conceded_points vs contested_points ratios."
        )
    )
    trust_score: float = Field(
        default=0.0,
        description=(
            "Final composite Trust Score (0.0–1.0) calculated as: "
            "trust_score = (evidence_validity_score * 0.40) "
            "+ (graph_consistency_score * 0.35) "
            "+ (agent_agreement_score * 0.15) "
            "+ ((1.0 - adjusted_confidence_penalty) * 0.10). "
            "Do NOT hardcode this value; compute it from the other fields."
        )
    )


# ──────────────────────────────────────────────
# Base Agent
# ──────────────────────────────────────────────
class BaseAgent:
    def __init__(self, name: str, role: str, goals: str, constraints: str):
        self.name = name
        self.role = role
        self.goals = goals
        self.constraints = constraints

    def build_system_prompt(self) -> str:
        return f"""You are the {self.name}.
Role: {self.role}
Goals: {self.goals}
Constraints: {self.constraints}

You are participating in a Multi-Agent Reasoning Council to resolve a repository divergence conflict.
The context you receive contains:
- diff_preview: the raw unified diff
- upstream_file_content: the full file as it exists in the upstream repository
- fork_file_content: the full file as it exists in the fork
- upstream_commit_messages: git log messages explaining WHY upstream made changes
- ast_summary: a structured diff of added/removed/modified functions and classes

RULES:
1. Ground ALL evidence in the provided context. Reference specific function names, class names, or line numbers.
2. DO NOT invent variable names, function signatures, or commit messages that are not in the context.
3. If the context is insufficient to form a grounded claim, say so explicitly rather than speculating.
4. When citing evidence, you MUST mark it as verified ONLY if you are absolutely certain it is in the context. UNVERIFIED evidence will be rejected by the Judge.
5. NEVER cite unverified evidence. Hallucinations will be penalized heavily.
"""
