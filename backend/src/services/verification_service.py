import ast
import subprocess
import tempfile
import os

class VerificationService:
    def verify_proposal(self, code_snippet: str) -> dict:
        """
        Validates syntax via AST and runs Ruff to detect structural/linting errors.
        Returns a dict indicating success and any error details.
        """
        result = {
            "success": False,
            "ast_valid": False,
            "ruff_valid": False,
            "errors": []
        }

        # 1. AST Validation
        try:
            ast.parse(code_snippet)
            result["ast_valid"] = True
        except SyntaxError as e:
            result["errors"].append(f"AST SyntaxError: {e}")
            return result

        # 2. Ruff Validation
        try:
            # Create a temporary file to run ruff against
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(code_snippet)
                temp_file_path = temp_file.name

            # Run Ruff
            process = subprocess.run(
                ["uv", "run", "ruff", "check", temp_file_path, "--isolated", "--output-format=json"],
                capture_output=True,
                text=True
            )
            
            if process.returncode == 0:
                result["ruff_valid"] = True
                result["success"] = True
            else:
                # Ruff returns 1 if there are linting errors
                result["errors"].append("Ruff Validation Failed")
        except Exception as e:
            result["errors"].append(f"Ruff execution failed: {e}")
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            
        return result

    def calculate_trust_score(self, verification_success: float, evidence_coverage: float, consensus_strength: float, structural_integrity: float) -> dict:
        """
        Calculates the explicit Trust Score.
        Trust = 0.35 * Verification Success + 0.25 * Evidence Coverage + 0.20 * Consensus Strength + 0.20 * Structural Integrity
        """
        final_trust = (
            (0.35 * verification_success) +
            (0.25 * evidence_coverage) +
            (0.20 * consensus_strength) +
            (0.20 * structural_integrity)
        )
        
        return {
            "verification_success": verification_success,
            "evidence_coverage": evidence_coverage,
            "consensus_strength": consensus_strength,
            "structural_integrity": structural_integrity,
            "final_trust": round(final_trust, 4)
        }
