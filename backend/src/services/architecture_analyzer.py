import ast
import os
import re

class ArchitectureAnalyzerService:
    def __init__(self, base_dir: str = "data/repos"):
        self.base_dir = os.path.abspath(base_dir)

    def analyze_hunk_impact(self, repo_path: str, file_path: str, diff_hunk: str) -> dict:
        """
        Analyzes a diff hunk to extract AST-level symbol information and architectural impact.
        Returns a dict with module, symbol, symbol_type, impact_radius, callers, dependencies, architectural_layer.
        """
        default_impact = {
            "module": file_path.replace("/", "."),
            "symbol": "Unknown",
            "symbol_type": "unknown",
            "impact_radius": 0,
            "callers": [],
            "dependencies": [],
            "architectural_layer": "Unknown Layer"
        }

        if not file_path.endswith(".py"):
            return default_impact

        full_path = os.path.join(repo_path, file_path)
        if not os.path.exists(full_path):
            return default_impact

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            tree = ast.parse(content)
        except Exception:
            return default_impact

        # Extract line numbers from diff_hunk
        # @@ -45,7 +45,7 @@
        lines_affected = []
        for line in diff_hunk.split('\n'):
            if line.startswith('@@'):
                m = re.search(r'\+(\d+)(?:,\d+)? @@', line)
                if m:
                    lines_affected.append(int(m.group(1)))

        if not lines_affected:
            return default_impact

        target_line = lines_affected[0]

        # Find which node contains the target line
        found_symbol = "Global Scope"
        symbol_type = "module"
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                    if node.lineno <= target_line <= node.end_lineno:
                        found_symbol = node.name
                        symbol_type = "class" if isinstance(node, ast.ClassDef) else "function"
                        break

        # Mock dependencies / callers / layer for now based on file path (demo purposes)
        # In a real system, we'd build a full dependency graph.
        layer = "Domain Logic"
        if "auth" in file_path or "jwt" in file_path:
            layer = "Authentication"
        elif "payment" in file_path:
            layer = "Payment Service"
        elif "cache" in file_path or "redis" in file_path:
            layer = "Caching Layer"
        elif "api" in file_path or "routes" in file_path:
            layer = "API / Presentation"
        elif "db" in file_path or "models" in file_path:
            layer = "Data Access"

        return {
            "module": file_path.replace("/", ".").replace(".py", ""),
            "symbol": found_symbol,
            "symbol_type": symbol_type,
            "impact_radius": len(diff_hunk.split('\n')) * 2, # simple proxy
            "callers": [f"caller_{i}()" for i in range(1, 4)], # mock data
            "dependencies": ["sqlalchemy", "pydantic"] if layer == "Data Access" else ["fastapi", "logging"],
            "architectural_layer": layer
        }

    def detect_layer_violations(self, repo_path: str) -> list:
        # Placeholder for full layer violation detection
        return []

    def detect_pattern_changes(self, repo_path: str) -> list:
        # Placeholder for structural pattern changes
        return []
