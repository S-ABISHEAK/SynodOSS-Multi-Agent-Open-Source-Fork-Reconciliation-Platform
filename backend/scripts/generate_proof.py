import sys
import os
import shutil
from git import Repo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.database import SessionLocal
from src.services.persistence_service import PersistenceService
from src.models.schema import Repository, RepositoryType, ReconciliationUnit
from src.workers.tasks import run_repository_scan
import json

def setup_test_repos():
    base_dir = os.path.join(os.getcwd(), "data", "test_repos")
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)
    os.makedirs(base_dir, exist_ok=True)
    
    up_path = os.path.join(base_dir, "upstream")
    fork_path = os.path.join(base_dir, "fork")
    
    # Init upstream
    up_repo = Repo.init(up_path)
    file_path = os.path.join(up_path, "api.py")
    with open(file_path, "w") as f:
        f.write("def login(username, password):\n    return True\n")
    up_repo.index.add(["api.py"])
    up_repo.index.commit("Initial commit in upstream")
    
    # Create fork by cloning upstream
    fork_repo = Repo.clone_from(up_path, fork_path)
    
    # Make change in upstream
    with open(file_path, "w") as f:
        f.write("def login(username, password, token=None):\n    return True\n")
    up_repo.index.add(["api.py"])
    up_repo.index.commit("Upstream added token auth to API")
    
    # Make conflicting change in fork
    fork_file_path = os.path.join(fork_path, "api.py")
    with open(fork_file_path, "w") as f:
        f.write("def login(username, password):\n    # Custom enterprise logger\n    print('Logging in...')\n    return True\n")
    fork_repo.index.add(["api.py"])
    fork_repo.index.commit("Fork added custom logging")
    
    return up_path, fork_path

def main():
    print("Setting up local test repositories...")
    up_path, fork_path = setup_test_repos()
    
    print("Initializing proof generation...")
    db = SessionLocal()
    
    upstream = Repository(url=up_path, type=RepositoryType.upstream)
    fork = Repository(url=fork_path, type=RepositoryType.fork)
    db.add_all([upstream, fork])
    db.commit()
    db.refresh(upstream)
    db.refresh(fork)
    
    persistence = PersistenceService(db)
    scan = persistence.store_scan(upstream.id, fork.id)
    
    print(f"Started scan ID {scan.id}...")
    run_repository_scan(scan.id, up_path, fork_path)
    
    print("Scan complete. Querying for ReconciliationUnits...")
    units = db.query(ReconciliationUnit).filter(ReconciliationUnit.scan_id == scan.id).all()
    
    if not units:
        print("No reconciliation units found!")
    else:
        unit = units[0]
        data = {
            "id": unit.id,
            "scan_id": unit.scan_id,
            "file_path": unit.file_path,
            "diff_hunk": unit.diff_hunk,
            "upstream_commits": unit.upstream_commits,
            "fork_commits": unit.fork_commits,
            "severity_score": unit.severity_score,
            "complexity_score": unit.complexity_score,
            "status": unit.status
        }
        print("\n--- ACTUAL DATABASE RECORD ---\n")
        print(json.dumps(data, indent=2))
        
        with open("proof_output.json", "w") as f:
            json.dump(data, f, indent=2)

        # ---------------------------------------------------------
        # PHASE 3 DEMO: Deterministic Verification Failure & Patch
        # ---------------------------------------------------------
        print("\n--- PHASE 3 VERIFICATION DEMO ---")
        from src.services.verification_service import VerificationService
        from src.services.patch_generator import PatchGenerator
        
        verifier = VerificationService()
        patcher = PatchGenerator()
        
        # 1. Failing Proposal (Undefined variable 'undefined_logger')
        failing_code = "def login(username, password, token=None):\n    undefined_logger('Logging in...')\n    return True\n"
        print("Testing FAILING Proposal (Undefined variable)...")
        fail_result = verifier.verify_proposal(failing_code)
        print(json.dumps(fail_result, indent=2))
        
        # 2. Passing Proposal (Corrected)
        passing_code = "def login(username, password, token=None):\n    print('Logging in...')\n    return True\n"
        print("\nTesting PASSING Proposal (Corrected)...")
        pass_result = verifier.verify_proposal(passing_code)
        print(json.dumps(pass_result, indent=2))
        
        # 3. Patch Generation
        if pass_result["success"]:
            print("\nGenerating Unified Git Patch...")
            plan = {
                "strategy": "ADAPTER_PATTERN",
                "target_file": "api.py",
                "target_content": "def login(username, password):\n    # Custom enterprise logger\n    print('Logging in...')\n    return True\n",
                "replacement_content": passing_code
            }
            # We pass the fork path to let it check applicability if possible
            patch_result = patcher.generate_patch(plan, repo_path=fork_path)
            print("Patch Applicability Passed:", patch_result["applicability_passed"])
            print("Metadata:", json.dumps(patch_result["metadata"], indent=2))
            print("\n--- PATCH.DIFF ---")
            print(patch_result["patch_content"])
            
    db.close()

if __name__ == "__main__":
    main()
