"""
CV reading utility using PyMuPDF.
Extracted from the original interview_prep_agent.py.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(_ROOT / ".env", override=True)

import pymupdf

# Default CV path — can be overridden via INTERVIEW_CV_PATH env var
_DEFAULT_CV = Path(os.getenv("INTERVIEW_CV_PATH", "Magdy_Mohamed_cv_ai.pdf"))
if not _DEFAULT_CV.is_absolute():
    # Look in agent/ directory first (legacy location), then root
    _AGENT_DIR = _ROOT / "agent"
    _candidate = _AGENT_DIR / _DEFAULT_CV
    if _candidate.exists():
        _DEFAULT_CV = _candidate
    else:
        _DEFAULT_CV = _ROOT / _DEFAULT_CV


def read_cv_text(cv_path: Path | None = None, max_chars: int = 12000) -> str:
    """Read a CV PDF and return its full text (up to max_chars characters).

    cv_path: Path to the PDF file. Defaults to the INTERVIEW_CV_PATH env var
             or the default CV location.

    Returns the text content, or an error message if the file is not found.
    """
    path = cv_path or _DEFAULT_CV
    if not Path(path).exists():
        return (
            f"[CV not found at {path}. "
            "Set INTERVIEW_CV_PATH in .env to the correct path.]"
        )
    doc = pymupdf.open(str(path))
    pages = [page.get_text() for page in doc]
    doc.close()
    return "\n\n".join(pages)[:max_chars]
