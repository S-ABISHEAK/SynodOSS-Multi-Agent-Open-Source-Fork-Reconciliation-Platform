import os
import stat
import shutil
import hashlib
from git import Repo


def _force_rmtree(path: str) -> None:
    """Remove a directory tree, clearing read-only bits first (required on Windows
    where Git marks .git/objects/* files as read-only)."""
    def _on_error(func, fpath, exc_info):
        # Clear the read-only bit and retry
        os.chmod(fpath, stat.S_IWRITE)
        func(fpath)

    shutil.rmtree(path, onerror=_on_error)


class RepositoryService:
    def __init__(self, base_dir: str = "data/repos"):
        self.base_dir = os.path.abspath(base_dir)

    def _get_repo_path(self, scan_id: int, repo_type: str) -> str:
        return os.path.join(self.base_dir, str(scan_id), repo_type)

    def clone_repository(self, url: str, scan_id: int, repo_type: str) -> str:
        path = self._get_repo_path(scan_id, repo_type)
        if os.path.exists(path):
            _force_rmtree(path)
        os.makedirs(path, exist_ok=True)
        # Using full clone for accurate diffing
        Repo.clone_from(url, path)
        return path

    def get_repository_metadata(self, scan_id: int, repo_type: str) -> dict:
        path = self._get_repo_path(scan_id, repo_type)
        repo = Repo(path)
        default_branch = repo.active_branch.name
        latest_commit = repo.head.commit
        fingerprint_raw = f"{default_branch}_{latest_commit.hexsha}"
        fingerprint = hashlib.sha256(fingerprint_raw.encode()).hexdigest()
        
        return {
            "default_branch": default_branch,
            "fingerprint": fingerprint
        }

    def update_repository(self, scan_id: int, repo_type: str):
        path = self._get_repo_path(scan_id, repo_type)
        repo = Repo(path)
        repo.remotes.origin.pull()
