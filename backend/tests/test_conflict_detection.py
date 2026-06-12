from src.services.conflict_detection_service import ConflictDetectionService

def test_categorize_conflicts():
    service = ConflictDetectionService()
    
    assert service.categorize_conflicts("package.json") == "dependency"
    assert service.categorize_conflicts("src/api/routes.py") == "api"
    assert service.categorize_conflicts("config/settings.yaml") == "configuration"
    assert service.categorize_conflicts("src/security/auth.py") == "security"
    assert service.categorize_conflicts("src/models/user.py") == "architecture"

def test_calculate_conflict_severity():
    service = ConflictDetectionService()
    
    score, label = service.calculate_conflict_severity("package.json", "dependency")
    # Base weight (25) + dependency (40) = 65 -> HIGH
    assert label == "HIGH"
    
    score, label = service.calculate_conflict_severity("src/models/user.py", "architecture")
    # Base weight (25) + 0 = 25 -> LOW
    assert label == "LOW"

def test_detect_conflicts():
    service = ConflictDetectionService()
    files = ["package.json", "src/api/routes.py"]
    conflicts = service.detect_conflicts(files)
    
    assert len(conflicts) == 2
    assert conflicts[0]["file_path"] == "package.json"
    assert conflicts[0]["conflict_type"] == "dependency"
