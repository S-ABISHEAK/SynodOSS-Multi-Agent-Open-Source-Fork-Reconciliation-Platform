import os
import subprocess
from pathlib import Path
import shutil

BASE_DIR = Path("data/repos/demo")

def run_git(*args, cwd=None):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)

def setup_repo(repo_path: Path):
    if repo_path.exists():
        shutil.rmtree(repo_path)
    repo_path.mkdir(parents=True)
    run_git("init", cwd=repo_path)
    run_git("config", "user.email", "demo@synod.oss", cwd=repo_path)
    run_git("config", "user.name", "Synod Demo", cwd=repo_path)

def create_upstream():
    upstream = BASE_DIR / "upstream"
    setup_repo(upstream)
    
    # 1. Authentication Layer
    auth_content = """
class AuthService:
    def legacy_auth_check(self, user):
        return True
"""
    (upstream / "auth.py").write_text(auth_content)
    
    # 2. Payment Service
    payment_content = """
class PaymentGateway:
    def process_transaction(self, amount):
        return "SUCCESS"
"""
    (upstream / "payment.py").write_text(payment_content)
    
    # 3. Caching Layer
    cache_content = """
class CacheLayer:
    def get(self, key):
        return None
"""
    (upstream / "cache.py").write_text(cache_content)
    
    run_git("add", ".", cwd=upstream)
    run_git("commit", "-m", "Initial commit", cwd=upstream)

    # ── Upstream Changes ──
    # 1. JWT v3 Migration
    auth_v3 = """
class AuthService:
    def authenticate_request(self, jwt_token):
        # Migrated to JWT v3
        return True
"""
    (upstream / "auth.py").write_text(auth_v3)
    run_git("add", "auth.py", cwd=upstream)
    run_git("commit", "-m", "chore: Migrate to JWT v3 (CVE-2024-1234)", cwd=upstream)

    # 2. Payment Service New Interface
    payment_v2 = """
class PaymentGateway:
    def process_transaction_v2(self, amount, currency):
        return "SUCCESS_V2"
"""
    (upstream / "payment.py").write_text(payment_v2)
    run_git("add", "payment.py", cwd=upstream)
    run_git("commit", "-m", "feat: Support multi-currency transactions", cwd=upstream)

    # 3. Redis Migration
    cache_redis = """
class CacheLayer:
    def __init__(self):
        self.redis = Redis()
        
    def get(self, key):
        return self.redis.get(key)
"""
    (upstream / "cache.py").write_text(cache_redis)
    run_git("add", "cache.py", cwd=upstream)
    run_git("commit", "-m", "perf: Migrate from memory cache to Redis", cwd=upstream)

def create_fork():
    upstream = BASE_DIR / "upstream"
    fork = BASE_DIR / "fork"
    
    if fork.exists():
        shutil.rmtree(fork)
        
    run_git("clone", str(upstream), str(fork))
    run_git("config", "user.email", "fork@enterprise.com", cwd=fork)
    run_git("config", "user.name", "Enterprise Fork", cwd=fork)
    
    # Rewind fork to initial commit to simulate divergence
    run_git("reset", "--hard", "HEAD~3", cwd=fork)
    
    # ── Fork Customizations ──
    # 1. Custom RBAC in Auth
    auth_rbac = """
class AuthService:
    def legacy_auth_check(self, user):
        if not self.check_rbac_entitlements(user):
            return False
        return True
        
    def check_rbac_entitlements(self, user):
        # Custom Enterprise RBAC
        return user.role == "ADMIN"
"""
    (fork / "auth.py").write_text(auth_rbac)
    run_git("add", "auth.py", cwd=fork)
    run_git("commit", "-m", "feat: Add enterprise RBAC entitlements", cwd=fork)

    # 2. Fraud Detection in Payments
    payment_fraud = """
class PaymentGateway:
    def process_transaction(self, amount):
        if self.detect_fraud(amount):
            return "DECLINED"
        return "SUCCESS"
        
    def detect_fraud(self, amount):
        return amount > 10000
"""
    (fork / "payment.py").write_text(payment_fraud)
    run_git("add", "payment.py", cwd=fork)
    run_git("commit", "-m", "sec: Add transaction fraud detection", cwd=fork)

    # 3. Custom Memory Cache
    cache_memory = """
class CacheLayer:
    def __init__(self):
        self.memory = {}
        
    def get(self, key):
        if key in self.memory:
            return self.memory[key]
        return None
        
    def set(self, key, value):
        self.memory[key] = value
"""
    (fork / "cache.py").write_text(cache_memory)
    run_git("add", "cache.py", cwd=fork)
    run_git("commit", "-m", "perf: Implement custom in-memory cache", cwd=fork)

if __name__ == "__main__":
    print("Generating demo dataset...")
    create_upstream()
    create_fork()
    print(f"Done! Repositories created at {BASE_DIR}")
