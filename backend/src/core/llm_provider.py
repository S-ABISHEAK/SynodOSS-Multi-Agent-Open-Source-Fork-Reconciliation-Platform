from groq import Groq
import json
import logging
from src.core.config import settings
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Max INPUT tokens sent per request — prevents runaway context costs.
# llama-3.1-8b-instant has a 128k context window, but we cap at 2500 tokens
# of input to stay well within the free-tier TPD budget (100k/day shared).
# 7 agents × 2500 input = 17500 input tokens per debate maximum.
MAX_INPUT_TOKENS = 2500
_CHARS_PER_TOKEN = 4  # fast approximation

# Per-role output caps: smaller roles get fewer output tokens to save budget.
AGENT_MAX_TOKENS = {
    "impact_analyst":   512,
    "advocate":         600,
    "defender":         600,
    "architect":        700,
    "advocate_rebuttal": 400,
    "defender_rebuttal": 400,
    "judge":            512,
    "default":          600,
}


class LLMProvider:
    def __init__(self):
        self.model = "llama-3.1-8b-instant"
        if settings.GROQ_API_KEY:
            self.client = Groq(api_key=settings.GROQ_API_KEY)
        else:
            self.client = None

    @staticmethod
    def _hard_cap_prompt(text: str, max_tokens: int = MAX_INPUT_TOKENS) -> str:
        """Truncate prompt text to stay within the token budget."""
        max_chars = max_tokens * _CHARS_PER_TOKEN
        if len(text) <= max_chars:
            return text
        suffix = "\n... [CONTEXT TRUNCATED — token budget enforced]"
        return text[: max_chars - len(suffix)] + suffix

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: type[BaseModel] = None,
        agent_role: str = "default",
    ) -> dict:
        max_output_tokens = AGENT_MAX_TOKENS.get(agent_role, AGENT_MAX_TOKENS["default"])

        # ── Hard-cap inputs ──────────────────────────────────────────
        system_prompt = self._hard_cap_prompt(system_prompt, max_tokens=400)
        user_prompt = self._hard_cap_prompt(user_prompt, max_tokens=MAX_INPUT_TOKENS)

        input_est = (len(system_prompt) + len(user_prompt)) // _CHARS_PER_TOKEN
        logger.info(
            f"[llm] role={agent_role} input_est={input_est}tok "
            f"max_output={max_output_tokens}tok model={self.model}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        if schema:
            schema_instruction = (
                "\n\nCRITICAL: You MUST output ONLY valid JSON matching this schema:\n"
                f"{json.dumps(schema.model_json_schema())}"
            )
            messages[0]["content"] += schema_instruction

        # If no API key, use structured mock that matches the real schemas
        if not self.client:
            logger.warning("GROQ_API_KEY is not set. Using structured mock LLM response.")
            return self._mock_response(schema)

        import time
        max_retries = 5
        base_delay = 2

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    messages=messages,
                    model=self.model,
                    temperature=0.2,
                    max_tokens=max_output_tokens,
                    response_format={"type": "json_object"} if schema else None
                )

                usage = getattr(response, "usage", None)
                if usage:
                    logger.info(
                        f"[llm] role={agent_role} "
                        f"prompt_tokens={usage.prompt_tokens} "
                        f"completion_tokens={usage.completion_tokens} "
                        f"total_tokens={usage.total_tokens}"
                    )

                content = response.choices[0].message.content
                if schema:
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON from LLM response: {content[:200]}")
                        if attempt == max_retries - 1:
                            raise ValueError(f"LLM returned invalid JSON: {content}") from e
                        continue
                return {"content": content}

            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "rate limit" in error_str:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        f"[llm] rate limit hit. Retrying in {delay}s "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(delay)
                    if attempt == max_retries - 1:
                        logger.error("[llm] Exhausted all retries for rate limits.")
                        raise e
                else:
                    import traceback
                    traceback.print_exc()
                    logger.error(f"[llm] Generation error: {e}")
                    raise e

    def _mock_response(self, schema) -> dict:
        """Generate a structured mock response that exactly matches the Pydantic schemas."""
        import time
        time.sleep(0.5)  # Simulate latency

        if schema is None:
            return {"content": "Mock analysis: The divergence appears to be a moderate refactoring."}

        schema_name = schema.__name__

        if schema_name == "AgentResponseSchema":
            return {
                "agent_role": "mock_agent",
                "analysis": (
                    "Mock analysis: The upstream changes refactor the authentication middleware. "
                    "The ast_summary shows `authenticate_request` was added in upstream while "
                    "`legacy_auth_check` was removed — indicating a deliberate security improvement. "
                    "The upstream commit message references CVE-2024-1234, making adoption strongly recommended."
                ),
                "evidence_provided": [
                    {"source": "ast_summary", "description": "Upstream added `authenticate_request`, removing `legacy_auth_check`", "line_start": None, "line_end": None, "strength": 0.90},
                    {"source": "upstream_commits", "description": "Upstream commit references CVE-2024-1234 security fix", "line_start": None, "line_end": None, "strength": 0.85},
                    {"source": "diff_hunk", "description": "Lines 1-15 show complete replacement of auth logic", "line_start": 1, "line_end": 15, "strength": 0.80},
                ],
                "proposed_action": "Apply upstream security patch with adapter to preserve fork rate-limiting.",
                "confidence": 0.87,
            }

        if schema_name == "RebuttalSchema":
            return {
                "agent_role": "mock_rebuttal",
                "rebuttal": (
                    "While the opposing argument raises valid security concerns, it ignores that "
                    "`fork_file_content` contains `compliance_logger()` at line 42 — a SOC2-required "
                    "audit trail that the upstream version completely removes. Accepting upstream as-is "
                    "would create a compliance violation."
                ),
                "conceded_points": [
                    "The CVE-2024-1234 security fix is legitimate and must be addressed."
                ],
                "contested_points": [
                    "`compliance_logger()` exists in fork but is absent from upstream — this is a material omission.",
                    "The upstream commit message does not mention compliance requirements at all."
                ],
                "evidence_provided": [
                    {"source": "fork_file", "description": "`compliance_logger()` found in fork but absent from upstream ast_summary", "line_start": None, "line_end": None, "strength": 0.88},
                ],
                "confidence": 0.82,
            }

        if schema_name == "ArchitectResolutionSchema":
            return {
                "agent_role": "Architect Reviewer",
                "resolution_action": "REFACTOR_ADAPTER",
                "rationale": (
                    "Both agents raised valid points. The upstream security fix (CVE-2024-1234) must be adopted. "
                    "However, the Defender correctly identified that `compliance_logger()` from the fork is "
                    "SOC2-required and cannot be dropped. A REFACTOR_ADAPTER solution resolves both concerns: "
                    "wrap the new upstream `authenticate_request()` in a `ComplianceAwareAuthAdapter` that "
                    "calls `compliance_logger()` before delegating to the upstream implementation."
                ),
                "implementation_steps": [
                    "Create `ComplianceAwareAuthAdapter` class that wraps `authenticate_request()`.",
                    "Move `compliance_logger()` from fork into the adapter's `__call__` method.",
                    "Replace all call-sites of `legacy_auth_check()` with `ComplianceAwareAuthAdapter`.",
                    "Add unit tests covering both the security path and the compliance logging path.",
                    "Run security audit to confirm CVE-2024-1234 is fully mitigated.",
                ],
                "evidence_provided": [
                    {"source": "ast_summary", "description": "`authenticate_request` added upstream, `legacy_auth_check` removed", "line_start": None, "line_end": None, "strength": 0.90},
                    {"source": "fork_file", "description": "`compliance_logger` present in fork, absent from upstream", "line_start": None, "line_end": None, "strength": 0.88},
                ],
                "confidence": 0.91,
            }

        if schema_name == "VerificationResponseSchema":
            return {
                "agent_role": "Verification Judge",
                "verification_summary": (
                    "Verified 3 of 4 evidence items across all rounds. "
                    "`authenticate_request` and `legacy_auth_check` are confirmed in ast_summary. "
                    "`compliance_logger` is confirmed in fork_file_content. "
                    "One claim referencing 'line 42' could not be verified — the diff only has 30 lines — marked UNGROUNDED."
                ),
                "invalidated_claims": [
                    "Line 42 reference for compliance_logger: diff_preview only contains 30 lines."
                ],
                "verified_evidence_count": 3,
                "adjusted_confidence_penalty": 0.08,
                "evidence_validity_score": 0.75,
                "graph_consistency_score": 0.90,
                "agent_agreement_score": 0.50,
                "trust_score": 0.88,
            }

        # Generic fallback for unknown schemas
        mock_data = {}
        for field_name, field_info in schema.model_fields.items():
            ann = field_info.annotation
            if ann == str:
                mock_data[field_name] = f"Mock {field_name}"
            elif ann == float:
                mock_data[field_name] = 0.85
            elif ann == int:
                mock_data[field_name] = 3
            elif ann == bool:
                mock_data[field_name] = True
            elif ann == list or str(ann).startswith("typing.List") or str(ann).startswith("list["):
                mock_data[field_name] = []
            else:
                mock_data[field_name] = None
        return mock_data

    def evaluate(self, text: str) -> float:
        return 0.85
