class ConflictDetectionService:
    def detect_conflicts(self, changed_files: list) -> list:
        conflicts = []
        for file in changed_files:
            if not file:
                continue
            ctype = self.categorize_conflicts(file)
            severity_score, severity_label = self.calculate_conflict_severity(file, ctype)
            conflicts.append({
                "file_path": file,
                "conflict_type": ctype,
                "severity": severity_label,
                "summary": f"Detected potential {ctype} conflict in {file} (Score: {severity_score})"
            })
        return conflicts

    def categorize_conflicts(self, file_path: str) -> str:
        fp = file_path.lower()
        if 'package.json' in fp or 'requirements.txt' in fp or 'pom.xml' in fp or 'go.mod' in fp:
            return "dependency"
        if 'api' in fp or 'routes' in fp or 'controller' in fp:
            return "api"
        if 'config' in fp or '.env' in fp or '.yaml' in fp or '.yml' in fp:
            return "configuration"
        if 'security' in fp or 'auth' in fp:
            return "security"
        return "architecture"

    def calculate_conflict_severity(self, file_path: str, conflict_type: str) -> tuple[int, str]:
        files_affected_weight = 10
        change_frequency_weight = 15
        
        dependency_impact_weight = 40 if conflict_type == "dependency" else 0
        api_breakage_weight = 35 if conflict_type == "api" else 0
        security_weight = 50 if conflict_type == "security" else 0
        
        severity_score = (
            files_affected_weight + 
            change_frequency_weight + 
            dependency_impact_weight + 
            api_breakage_weight + 
            security_weight
        )
        
        if severity_score < 30:
            label = "LOW"
        elif severity_score < 60:
            label = "MEDIUM"
        elif severity_score < 80:
            label = "HIGH"
        else:
            label = "CRITICAL"
            
        return severity_score, label

    def calculate_complexity(self, diff_hunk: str) -> float:
        complexity = 1.0
        if not diff_hunk:
            return complexity
            
        keywords = ['if ', 'else', 'elif', 'for ', 'while ', 'switch', 'case', 'catch', 'except', '&&', '||', 'and ', 'or ']
        for line in diff_hunk.split('\n'):
            if line.startswith('+') or line.startswith('-'):
                for kw in keywords:
                    if kw in line:
                        complexity += 0.5
        return complexity
