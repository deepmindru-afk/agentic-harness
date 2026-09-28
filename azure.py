"""Azure Foundry client for the agentic harness.

Handles the one non-obvious routing rule: Claude deployments on Azure answer
only via the Responses API, everything else via chat/completions.

DEFAULT/DEEP remain the registry defaults for hosted slots; prefer
model_router.model_for(task_class) / complete_for(task_class, prompt) in
application code instead of passing deployment names directly.
"""
from __future__ import annotations

import os
import json
import urllib.request
import urllib.error

from engineering import with_retry, TransientError

BASE = os.environ.get(
    'AZURE_FOUNDRY_BASE_URL',
    'https://admin-3443-resourche.openai.azure.com/openai/v1')
KEY = os.environ.get('AZURE_FOUNDRY_API_KEY', '')

# Registry defaults (also registered in model_router.CAPABILITY_SLOTS)
DEFAULT = 'gpt-5.6-sol'
DEEP = 'claude-opus-5'
EMBED = 'text-embedding-3-small'

RESPONSES_ONLY = ('claude',)
BACKOFF_CODES = {429, 500, 502, 503, 504}


def _post(path: str, payload: dict, timeout: int = 180) -> dict:
    if not KEY:
        raise RuntimeError('AZURE_FOUNDRY_API_KEY is not set')
    req = urllib.request.Request(
        f'{BASE}{path}',
        data=json.dumps(payload).encode(),
        headers={'api-key': KEY, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code in BACKOFF_CODES:
            raise TransientError(f'Azure {e.code} on {path}') from e
        raise


def complete(prompt: str, *, model: str = DEFAULT, max_tokens: int = 4000,
             system: str | None = None) -> str:
    """Single completion with retry/backoff. Routes Claude to /responses."""

    def _call():
        if any(m in model.lower() for m in RESPONSES_ONLY):
            d = _post('/responses', {'model': model, 'input': prompt,
                                     'max_output_tokens': max_tokens})
            parts = []
            for o in d.get('output', []):
                for c in o.get('content', []) or []:
                    if c.get('text'):
                        parts.append(c['text'])
            return '\n'.join(parts)
        msgs = ([{'role': 'system', 'content': system}] if system else []) + \
               [{'role': 'user', 'content': prompt}]
        d = _post('/chat/completions', {'model': model, 'messages': msgs,
                                        'max_completion_tokens': max_tokens})
        return d['choices'][0]['message'].get('content', '')

    return with_retry(_call)()


def embed(text: str | list[str], *, model: str = EMBED) -> list:
    d = _post('/embeddings', {'model': model, 'input': text})
    return [x['embedding'] for x in d['data']]


def llm(prompt: str, *, model: str | None = None, task_class: str | None = None) -> str:
    """General completion. Prefer task_class so model_router selects the slot."""
    if model is None and task_class:
        try:
            from model_router import model_for
            model = model_for(task_class)
        except Exception:
            model = DEFAULT
    return complete(prompt, model=model or DEFAULT)


def deep(prompt: str, *, model: str | None = None, task_class: str = 'plan') -> str:
    """Deep-reasoning completion; default task_class=plan → hosted_reasoning."""
    if model is None:
        try:
            from model_router import model_for
            model = model_for(task_class)
        except Exception:
            model = DEEP
    return complete(prompt, model=model or DEEP)


__all__ = ['complete', 'embed', 'llm', 'deep', 'DEFAULT', 'DEEP', 'EMBED']
