from pydantic import BaseModel, Field
from typing import List, Optional
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
    source: str = Field(
        ...,
        description="Where the evidence comes from: 'upstream_file', 'fork_file', 'diff_hunk', 'upstream_commits', 'fork_commits', 'ast_summary'"
    )
    description: str = Field(
        ...,
        description="What the evidence shows. Reference specific function/class names from ast_summary."
    )
    line_start: Optional[int] = Field(
        None,
        description="Starting line number in the diff_preview that supports this claim. Required if source is 'diff_hunk'."
    )
    line_end: Optional[int] = Field(
        None,
        description="Ending line number in the diff_preview that supports this claim. Required if source is 'diff_hunk'."
    )
    strength: float = Field(
        ...,
        description="Confidence in this evidence from 0.0 (speculation) to 1.0 (directly verifiable in the provided code)"
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
    resolution_action: ResolutionAction = Field(
        ...,
        description=(
            "You MUST choose exactly one of: ACCEPT_UPSTREAM, REJECT_UPSTREAM, "
            "MERGE_PARTIAL, REFACTOR_ADAPTER, ESCALATE_HUMAN"
        )
    )
    rationale: str = Field(
        ...,
        description="Why you chose this action. Must reference specific symbols from ast_summary and arguments from the debate."
    )
    implementation_steps: List[str] = Field(
        default_factory=list,
        description="Concrete, ordered steps to execute the resolution. Reference function names and line numbers."
    )
    evidence_provided: List[Evidence] = Field(
        default_factory=list,
        description="Evidence grounding your architectural decision."
    )
    confidence: float = Field(
        ...,
        description="How confident you are in this architectural decision (0.0 to 1.0)"
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
4. When citing diff_hunk evidence, provide line_start and line_end from the diff_preview.
"""
