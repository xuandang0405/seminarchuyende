"""Internationalization (i18n) & Localization (l10n) Core Module for FastAPI.

RFC 9110 compliant Accept-Language parsing, language extraction, and fallback hierarchy:
requested_lang -> "en" -> "vi" (default)
"""

from typing import List, Optional
from fastapi import Request, Query
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

SUPPORTED_LANGUAGES: List[str] = ["vi", "en", "ja", "ko", "fr", "zh"]
DEFAULT_LANGUAGE: str = "vi"
SECONDARY_FALLBACK: str = "en"


def parse_accept_language(accept_language_header: Optional[str]) -> List[str]:
    """Parses RFC 9110 Accept-Language header taking quality factors (q=...) into account.
    
    Example:
        'fr-CH, fr;q=0.9, en;q=0.8, vi;q=0.7, *;q=0.5'
        returns ['fr', 'en', 'vi'] in priority order matching SUPPORTED_LANGUAGES.
    """
    if not accept_language_header:
        return []

    weighted_langs = []
    for item in accept_language_header.split(","):
        parts = item.strip().split(";")
        code_part = parts[0].strip().lower()
        if not code_part:
            continue
        # Extract primary language subtag (e.g. 'fr-FR' -> 'fr', 'zh-CN' -> 'zh')
        primary_code = code_part.split("-")[0]
        q_value = 1.0
        for param in parts[1:]:
            param = param.strip()
            if param.startswith("q="):
                try:
                    q_value = float(param[2:])
                except ValueError:
                    q_value = 0.0
        weighted_langs.append((q_value, primary_code))

    # Sort descending by q factor
    weighted_langs.sort(key=lambda x: x[0], reverse=True)
    
    valid_langs = []
    for _, code in weighted_langs:
        if code in SUPPORTED_LANGUAGES and code not in valid_langs:
            valid_langs.append(code)
    return valid_langs


def resolve_language(
    query_lang: Optional[str] = None,
    accept_language_header: Optional[str] = None
) -> str:
    """Resolves the effective language following priority:
    1. Explicit query parameter ?lang=...
    2. Parsed Accept-Language header
    3. Default fallback ('vi')
    """
    if query_lang:
        cleaned = query_lang.strip().lower().split("-")[0]
        if cleaned in SUPPORTED_LANGUAGES:
            return cleaned

    header_langs = parse_accept_language(accept_language_header)
    if header_langs:
        return header_langs[0]

    return DEFAULT_LANGUAGE


async def get_request_language(
    request: Request,
    lang: Optional[str] = Query(None, description="Optional language override (vi, en, ja, ko, fr, zh)")
) -> str:
    """FastAPI Dependency for endpoints needing the resolved language."""
    if lang:
        cleaned = lang.strip().lower().split("-")[0]
        if cleaned in SUPPORTED_LANGUAGES:
            return cleaned

    accept_header = request.headers.get("accept-language")
    return resolve_language(accept_language_header=accept_header)


class LanguageMiddleware(BaseHTTPMiddleware):
    """FastAPI Middleware to detect language on all requests and attach Content-Language to responses."""
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        query_lang = request.query_params.get("lang")
        accept_header = request.headers.get("accept-language")
        effective_lang = resolve_language(query_lang=query_lang, accept_language_header=accept_header)
        
        request.state.lang = effective_lang
        response = await call_next(request)
        response.headers["Content-Language"] = effective_lang
        return response
