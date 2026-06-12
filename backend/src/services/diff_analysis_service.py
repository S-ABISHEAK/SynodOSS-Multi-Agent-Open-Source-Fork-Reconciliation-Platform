import os
from git import Repo

class DiffAnalysisService:
    def __init__(self, base_dir: str = "data/repos"):
        self.base_dir = os.path.abspath(base_dir)
        
    def _get_repo_path(self, scan_id: int, repo_type: str) -> str:
        return os.path.join(self.base_dir, str(scan_id), repo_type)

    def get_commit_gap(self, upstream_path: str, fork_path: str) -> dict:
        try:
            upstream_repo = Repo(upstream_path)
            fork_repo = Repo(fork_path)
            
            upstream_count = len(list(upstream_repo.iter_commits()))
            fork_count = len(list(fork_repo.iter_commits()))
            
            gap = abs(upstream_count - fork_count)
        except Exception:
            upstream_count = 0
            fork_count = 0
            gap = 0
            
        return {
            "upstream_commit_count": upstream_count,
            "fork_commit_count": fork_count,
            "commit_gap": gap
        }

    def get_changed_files(self, upstream_path: str, fork_path: str) -> dict:
        try:
            fork_repo = Repo(fork_path)
            if 'upstream_synod' not in [r.name for r in fork_repo.remotes]:
                fork_repo.create_remote('upstream_synod', upstream_path)
            fork_repo.remotes.upstream_synod.fetch()
            
            fork_head = fork_repo.head.commit
            if 'HEAD' in fork_repo.remotes.upstream_synod.refs:
                upstream_head = fork_repo.commit('upstream_synod/HEAD')
            else:
                upstream_head = fork_repo.remotes.upstream_synod.refs[0].commit
            
            diffs = upstream_head.diff(fork_head)
            added = 0
            deleted = 0
            changed = 0
            files = []
            
            for d in diffs:
                files.append(d.b_path or d.a_path)
                if d.new_file:
                    added += 1
                elif d.deleted_file:
                    deleted += 1
                else:
                    changed += 1
                    
            return {
                "added_files": added,
                "deleted_files": deleted,
                "changed_files": changed,
                "files_list": files
            }
        except Exception:
            return {
                "added_files": 0,
                "deleted_files": 0,
                "changed_files": 0,
                "files_list": []
            }
            
    def calculate_divergence(self, scan_id: int) -> dict:
        upstream_path = self._get_repo_path(scan_id, "upstream")
        fork_path = self._get_repo_path(scan_id, "fork")
        
        gap_info = self.get_commit_gap(upstream_path, fork_path)
        file_info = self.get_changed_files(upstream_path, fork_path)
        
        return {
            **gap_info,
            "added_files": file_info["added_files"],
            "deleted_files": file_info["deleted_files"],
            "changed_files": file_info["changed_files"],
            "files_list": file_info["files_list"]
        }

    def extract_reconciliation_units(self, upstream_path: str, fork_path: str) -> list:
        units = []
        try:
            fork_repo = Repo(fork_path)
            if 'upstream_synod' not in [r.name for r in fork_repo.remotes]:
                fork_repo.create_remote('upstream_synod', upstream_path)
            fork_repo.remotes.upstream_synod.fetch()
            
            raw_diff_text = fork_repo.git.diff('upstream_synod/HEAD', 'HEAD', unified=3)
            # Remove any utf-16 surrogate characters that might break database insertion
            import re
            diff_text = re.sub(r'[\ud800-\udfff]', '', raw_diff_text)
            
            current_file = None
            current_hunk = []
            
            lines = diff_text.split('\n')
            for line in lines:
                if line.startswith('diff --git'):
                    if current_file and current_hunk:
                        units.append({
                            "file_path": current_file,
                            "diff_hunk": '\n'.join(current_hunk),
                            "upstream_commits": [],
                            "fork_commits": []
                        })
                        current_hunk = []
                    parts = line.split(' ')
                    current_file = parts[-1].replace('b/', '', 1) if parts[-1].startswith('b/') else parts[-1]
                elif line.startswith('@@'):
                    if current_hunk:
                        units.append({
                            "file_path": current_file,
                            "diff_hunk": '\n'.join(current_hunk),
                            "upstream_commits": [],
                            "fork_commits": []
                        })
                    current_hunk = [line]
                elif current_file and current_hunk:
                    current_hunk.append(line)
                    
            if current_file and current_hunk:
                units.append({
                    "file_path": current_file,
                    "diff_hunk": '\n'.join(current_hunk),
                    "upstream_commits": [],
                    "fork_commits": []
                })
                
            from src.services.architecture_analyzer import ArchitectureAnalyzerService
            analyzer = ArchitectureAnalyzerService(self.base_dir)

            for unit in units:
                fp = unit["file_path"]
                try:
                    up_commits = fork_repo.git.log('upstream_synod/HEAD', '--format=%H', '--', fp).split()[:5]
                    fork_commits = fork_repo.git.log('HEAD', '--not', 'upstream_synod/HEAD', '--format=%H', '--', fp).split()[:5]
                    unit["upstream_commits"] = up_commits
                    unit["fork_commits"] = fork_commits

                    # Run AST extraction & impact analysis
                    impact = analyzer.analyze_hunk_impact(fork_path, fp, unit["diff_hunk"])
                    unit.update(impact)

                except Exception:
                    # Apply defaults if git log or ast parsing fails
                    unit["upstream_commits"] = []
                    unit["fork_commits"] = []
                    unit.update({
                        "module": fp,
                        "symbol": "Unknown",
                        "symbol_type": "unknown",
                        "impact_radius": 0,
                        "callers": [],
                        "dependencies": [],
                        "architectural_layer": "Unknown Layer"
                    })
        except Exception as e:
            print(f"Failed to extract units: {e}")
        return units
