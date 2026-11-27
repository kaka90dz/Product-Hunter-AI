"""Stockage durable dans GitHub (branche « data » du dépôt privé) via l'API REST.

Le jeton n'a besoin que de : Contents (lecture/écriture) et Actions (lecture/écriture),
limités au seul dépôt Product-Hunter-AI."""
from __future__ import annotations

import base64

import requests

API = "https://api.github.com"
ACTIVE = {"queued", "in_progress", "waiting", "requested", "pending"}


class ConflictError(Exception):
    pass


class GitHubStore:
    def __init__(self, token: str, repo: str, branch: str = "data", workflow: str = "recherche.yml"):
        self.repo, self.branch, self.workflow = repo, branch, workflow
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                               "X-GitHub-Api-Version": "2022-11-28"})

    def _url(self, path: str) -> str:
        return f"{API}/repos/{self.repo}/{path}"

    def branch_sha(self) -> str:
        r = self.s.get(self._url(f"branches/{self.branch}"), timeout=20)
        r.raise_for_status()
        return r.json()["commit"]["sha"]

    def download(self, path: str) -> tuple[bytes, str]:
        """Retourne (contenu, sha du fichier)."""
        r = self.s.get(self._url(f"contents/{path}"), params={"ref": self.branch}, timeout=60)
        r.raise_for_status()
        meta = r.json()
        if meta.get("content") and meta.get("encoding") == "base64":
            return base64.b64decode(meta["content"]), meta["sha"]
        raw = self.s.get(self._url(f"contents/{path}"), params={"ref": self.branch}, timeout=120,
                         headers={"Accept": "application/vnd.github.raw"})
        raw.raise_for_status()
        return raw.content, meta["sha"]

    def upload(self, path: str, content: bytes, sha: str, message: str) -> str:
        r = self.s.put(self._url(f"contents/{path}"), timeout=120, json={
            "message": message, "content": base64.b64encode(content).decode(), "sha": sha, "branch": self.branch})
        if r.status_code in (409, 422):
            raise ConflictError("Le fichier a été modifié entre-temps")
        r.raise_for_status()
        return r.json()["content"]["sha"]

    def runs(self, n: int = 5) -> list[dict]:
        r = self.s.get(self._url(f"actions/workflows/{self.workflow}/runs"), params={"per_page": n}, timeout=20)
        r.raise_for_status()
        return r.json().get("workflow_runs", [])

    def active_run(self) -> dict | None:
        return next((r for r in self.runs() if r["status"] in ACTIVE), None)

    def dispatch(self, inputs: dict | None = None, ref: str = "main") -> None:
        if self.active_run():
            raise ConflictError("Une recherche est déjà en cours")
        r = self.s.post(self._url(f"actions/workflows/{self.workflow}/dispatches"), timeout=20,
                        json={"ref": ref, "inputs": inputs or {}})
        r.raise_for_status()
