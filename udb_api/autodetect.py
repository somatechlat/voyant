"""Auto-detection heuristics for data source hints (stub)."""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class DetectionCandidate:
    provider: str
    auth_type: str
    airbyte_source_def: Optional[str]
    config_template: dict
    confidence: float
    oauth_url: Optional[str] = None


@dataclass
class DetectionResult:
    best: DetectionCandidate
    candidates: List[DetectionCandidate]

# Simple patterns; to be expanded
SHAREPOINT_HOST = re.compile(r"sharepoint\.com", re.I)
GOOGLE_DRIVE_HOST = re.compile(r"drive\.googleapis\.com|googleapis\.com/drive", re.I)
POSTGRES_PATTERN = re.compile(r"^postgres(ql)?://", re.I)
S3_PATTERN = re.compile(r"^s3://", re.I)
WEB_DAV_PATTERN = re.compile(r"webdav", re.I)


def autodetect(hint: str) -> DetectionResult:
    h = hint.strip()
    candidates: List[DetectionCandidate] = []
    if SHAREPOINT_HOST.search(h):
        candidates.append(DetectionCandidate("sharepoint_onedrive", "oauth2", "0f6b...sharepoint-def", {"site_url": h, "drive": None}, 0.85))
    if GOOGLE_DRIVE_HOST.search(h):
        candidates.append(DetectionCandidate("google_drive", "oauth2", "1ab2...gdrive-def", {"drive_id": None}, 0.8))
    if POSTGRES_PATTERN.search(h):
        candidates.append(DetectionCandidate("postgres", "userpass", "4353...postgres-def", {"connection_string": h}, 0.9))
    if S3_PATTERN.search(h):
        candidates.append(DetectionCandidate("s3", "keys", "9c1d...s3-def", {"bucket": h.replace("s3://", "")}, 0.7))
    # Always include REST fallback
    candidates.append(DetectionCandidate("rest_api", "none", "1234...rest-def", {"base_url": h}, 0.4))
    # Determine best candidate
    best = max(candidates, key=lambda c: c.confidence)
    return DetectionResult(best=best, candidates=candidates)
