import os
import subprocess
import shutil
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
REPOS_DIR = BASE_DIR / "data" / "repos" / "demo"
UPSTREAM_DIR = REPOS_DIR / "upstream"
FORK_DIR = REPOS_DIR / "fork"

def run_git(cmd, cwd):
    subprocess.run(["git"] + cmd, cwd=cwd, check=True, capture_output=True)

def setup_repo(repo_dir):
    if repo_dir.exists():
        shutil.rmtree(repo_dir)
    os.makedirs(repo_dir)
    run_git(["init"], repo_dir)
    run_git(["config", "user.name", "Demo User"], repo_dir)
    run_git(["config", "user.email", "demo@example.com"], repo_dir)

def write_file(repo_dir, filename, content):
    path = repo_dir / filename
    os.makedirs(path.parent, exist_ok=True)
    with open(path, "w") as f:
        f.write(content)

# Setup
setup_repo(UPSTREAM_DIR)
setup_repo(FORK_DIR)

# --- BASE STATE (Common Ancestor) ---
print("Creating base state...")

base_auth = """def decode_token(token):
    # JWT v2
    return {"user": "admin"}
"""
base_payment = """class PaymentGateway:
    def process(self, amount):
        return True
"""
base_cache = """class Cache:
    def __init__(self):
        self.store = {}
    def get(self, key):
        return self.store.get(key)
    def set(self, key, val):
        self.store[key] = val
"""

write_file(UPSTREAM_DIR, "auth.py", base_auth)
write_file(UPSTREAM_DIR, "payment.py", base_payment)
write_file(UPSTREAM_DIR, "cache.py", base_cache)

run_git(["add", "."], UPSTREAM_DIR)
run_git(["commit", "-m", "Initial commit"], UPSTREAM_DIR)

# Copy base to fork
shutil.copytree(UPSTREAM_DIR / ".git", FORK_DIR / ".git", dirs_exist_ok=True)
run_git(["reset", "--hard", "HEAD"], FORK_DIR)

# --- UPSTREAM CHANGES ---
print("Simulating Upstream changes...")

up_auth = """def decode_token(token):
    # JWT v3 migration
    from jwt import decode, ExpiredSignatureError
    try:
        return decode(token, 'secret', algorithms=['HS256'])
    except ExpiredSignatureError:
        return None
"""
up_payment = """class PaymentGateway:
    def process_v2(self, amount, currency="USD"):
        # New API interface
        return {"status": "success", "amount": amount}
"""
up_cache = """class Cache:
    def __init__(self):
        import redis
        self.store = redis.Redis(host='localhost', port=6379, db=0)
    def get(self, key):
        return self.store.get(key)
    def set(self, key, val):
        self.store.set(key, val)
"""

write_file(UPSTREAM_DIR, "auth.py", up_auth)
run_git(["add", "auth.py"], UPSTREAM_DIR)
run_git(["commit", "-m", "feat: migrate to JWT v3"], UPSTREAM_DIR)

write_file(UPSTREAM_DIR, "payment.py", up_payment)
run_git(["add", "payment.py"], UPSTREAM_DIR)
run_git(["commit", "-m", "feat: introduce Payment API v2"], UPSTREAM_DIR)

write_file(UPSTREAM_DIR, "cache.py", up_cache)
run_git(["add", "cache.py"], UPSTREAM_DIR)
run_git(["commit", "-m", "perf: switch to Redis caching layer"], UPSTREAM_DIR)

# --- FORK CHANGES ---
print("Simulating Fork changes...")

fork_auth = """def decode_token(token):
    # JWT v2
    payload = {"user": "admin"}
    # Added RBAC customization
    payload["roles"] = ["superuser", "editor"]
    payload["permissions"] = {"read": True, "write": True}
    return payload
"""
fork_payment = """class PaymentGateway:
    def process(self, amount):
        # Fraud detection module
        if amount > 10000:
            raise Exception("Fraud detected: amount too large")
        return True
"""
fork_cache = """class Cache:
    def __init__(self):
        self.store = {}
        self.ttl = {} # Custom memory cache with TTL
    def get(self, key):
        if key in self.ttl and self.ttl[key] < current_time():
            del self.store[key]
        return self.store.get(key)
    def set(self, key, val, ttl=3600):
        self.store[key] = val
        self.ttl[key] = current_time() + ttl
"""

write_file(FORK_DIR, "auth.py", fork_auth)
run_git(["add", "auth.py"], FORK_DIR)
run_git(["commit", "-m", "custom: added advanced RBAC to auth"], FORK_DIR)

write_file(FORK_DIR, "payment.py", fork_payment)
run_git(["add", "payment.py"], FORK_DIR)
run_git(["commit", "-m", "sec: added high-value fraud detection"], FORK_DIR)

write_file(FORK_DIR, "cache.py", fork_cache)
run_git(["add", "cache.py"], FORK_DIR)
run_git(["commit", "-m", "perf: implemented custom TTL memory cache"], FORK_DIR)

print(f"Demo repositories generated at {REPOS_DIR}")
