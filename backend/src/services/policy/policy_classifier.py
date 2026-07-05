"""
policy_classifier.py

Classifies raw policy text into one of 15 predefined PolicyCategory values.
Deterministic keyword matching — no LLM call, no API cost.
"""
import re
import logging
from src.models.schema import PolicyCategory

logger = logging.getLogger(__name__)

# Keyword map: category → keywords (case-insensitive)
_CATEGORY_KEYWORDS: dict[PolicyCategory, list[str]] = {
    PolicyCategory.AUTHENTICATION: [
        "authentication", "login", "sso", "oauth", "jwt", "token", "session", "saml",
        "ldap", "mfa", "multi-factor", "password", "credential",
    ],
    PolicyCategory.AUTHORIZATION: [
        "authorization", "rbac", "role-based", "permission", "access control",
        "privilege", "acl", "entitlement", "scope",
    ],
    PolicyCategory.SECURITY: [
        "security", "vulnerability", "exploit", "threat", "penetration", "audit",
        "encryption", "tls", "ssl", "cve", "owasp", "cve", "secret", "sensitive",
    ],
    PolicyCategory.COMPLIANCE: [
        "compliance", "gdpr", "hipaa", "soc2", "pci", "iso 27001", "regulation",
        "legal", "privacy", "data protection", "dpa",
    ],
    PolicyCategory.NETWORKING: [
        "network", "firewall", "vpn", "port", "ip address", "dns", "proxy",
        "ingress", "egress", "subnet", "load balancer",
    ],
    PolicyCategory.LOGGING: [
        "logging", "audit log", "log level", "log format", "tracing", "telemetry",
        "observability", "monitoring", "alerting", "log retention",
    ],
    PolicyCategory.INFRASTRUCTURE: [
        "infrastructure", "kubernetes", "docker", "container", "cloud", "aws",
        "azure", "gcp", "terraform", "helm", "serverless",
    ],
    PolicyCategory.ARCHITECTURE: [
        "architecture", "microservice", "monolith", "design pattern", "coupling",
        "dependency", "interface", "module boundary", "service contract",
    ],
    PolicyCategory.PERFORMANCE: [
        "performance", "latency", "throughput", "cache", "response time", "timeout",
        "rate limit", "bottleneck", "optimization", "benchmark",
    ],
    PolicyCategory.DATABASE: [
        "database", "sql", "nosql", "migration", "schema", "index", "transaction",
        "backup", "postgresql", "mysql", "mongodb", "redis",
    ],
    PolicyCategory.API_STANDARDS: [
        "api", "rest", "graphql", "openapi", "swagger", "versioning", "endpoint",
        "http", "grpc", "webhook", "contract",
    ],
    PolicyCategory.TESTING: [
        "testing", "unit test", "integration test", "coverage", "tdd", "bdd",
        "mock", "assertion", "regression", "ci", "continuous integration",
    ],
    PolicyCategory.DEPLOYMENT: [
        "deployment", "release", "rollback", "blue-green", "canary", "pipeline",
        "ci/cd", "artifact", "environment", "staging", "production",
    ],
    PolicyCategory.CODING_STANDARDS: [
        "coding standard", "style guide", "linting", "formatting", "naming convention",
        "code review", "documentation", "comment", "refactor",
    ],
    PolicyCategory.ENTERPRISE_CUSTOM: [
        "enterprise", "internal", "proprietary", "custom", "business rule",
        "workflow", "approval", "escalation", "policy",
    ],
}


def classify_policy(text: str) -> PolicyCategory:
    """
    Classify policy text into the best-matching PolicyCategory.

    Returns the category with the highest keyword hit count.
    Falls back to ENTERPRISE_CUSTOM if no clear match.
    """
    text_lower = text.lower()
    scores: dict[PolicyCategory, int] = {cat: 0 for cat in PolicyCategory}

    for category, keywords in _CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            # Count occurrences of the keyword
            scores[category] += len(re.findall(r'\b' + re.escape(keyword) + r'\b', text_lower))

    best_category = max(scores, key=lambda c: scores[c])
    best_score = scores[best_category]

    if best_score == 0:
        logger.info("[policy_classifier] No keyword matches — defaulting to ENTERPRISE_CUSTOM")
        return PolicyCategory.ENTERPRISE_CUSTOM

    logger.info(f"[policy_classifier] Classified as {best_category.value} (score={best_score})")
    return best_category
