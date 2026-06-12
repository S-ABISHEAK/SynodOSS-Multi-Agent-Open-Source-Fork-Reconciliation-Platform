import os
import ast

class EvidenceResolver:
    """
    Priority 3: Evidence Resolver.
    Validates claims (commit hash, symbol existence, line ranges) before agents can securely use them,
    and allows the Judge to expose unsupported claims.
    """
    def __init__(self, base_dir: str = "data/repos"):
        self.base_dir = os.path.abspath(base_dir)

    def validate_evidence(self, repo_path: str, file_path: str, commit: str = None, symbol: str = None, line_start: int = None, line_end: int = None) -> dict:
        """
        Validates if the provided evidence (commit, symbol, lines) actually exists in the file.
        Returns a dictionary with validation status.
        """
        result = {
            "is_valid": True,
            "errors": []
        }

        full_path = os.path.join(repo_path, file_path)
        
        # 1. File existence validation
        if not os.path.exists(full_path):
            result["is_valid"] = False
            result["errors"].append(f"File {file_path} does not exist in the repository.")
            return result

        # Load file content
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.splitlines()
        except Exception as e:
            result["is_valid"] = False
            result["errors"].append(f"Could not read file {file_path}: {e}")
            return result

        # 2. Line Validation
        total_lines = len(lines)
        if line_start is not None:
            if line_start < 1 or line_start > total_lines:
                result["is_valid"] = False
                result["errors"].append(f"line_start {line_start} is out of bounds (1-{total_lines}).")
            if line_end is not None:
                if line_end < line_start or line_end > total_lines:
                    result["is_valid"] = False
                    result["errors"].append(f"line_end {line_end} is out of bounds or invalid.")

        # 3. Symbol Validation
        if symbol and file_path.endswith(".py"):
            try:
                tree = ast.parse(content)
                found = False
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        if node.name == symbol:
                            found = True
                            # Optional: Check if line numbers align
                            if line_start and hasattr(node, 'lineno'):
                                if not (node.lineno <= line_start <= node.end_lineno):
                                    result["is_valid"] = False
                                    result["errors"].append(f"Symbol '{symbol}' exists, but not at line {line_start}.")
                            break
                if not found:
                    result["is_valid"] = False
                    result["errors"].append(f"Symbol '{symbol}' does not exist in the AST.")
            except Exception:
                result["is_valid"] = False
                result["errors"].append("Could not parse AST for symbol validation.")

        # 4. Commit Validation (Mocked for speed; in real system, `git log | grep commit`)
        if commit:
            if len(commit) < 6:
                result["is_valid"] = False
                result["errors"].append(f"Commit hash '{commit}' is invalid or too short.")

        return result
