"""Thin adapters over the chat APIs. Plain urllib, no SDKs.

A model is named as ``provider/model``. Supported providers: ollama, openai,
groq, openrouter (all OpenAI-compatible), anthropic, gemini.
"""

import json
import os
import urllib.request

SYSTEM = "Answer with only the final answer. No explanation."

# OpenAI-compatible endpoints and the env var that holds their key.
OPENAI_LIKE = {
    "openai": ("https://api.openai.com/v1/chat/completions", "OPENAI_API_KEY"),
    "groq": ("https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1/chat/completions", "OPENROUTER_API_KEY"),
}


def _post(url, body, headers, timeout=120):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _key(var):
    key = os.environ.get(var)
    if not key:
        raise RuntimeError(f"set {var} to use this provider")
    return key


def build_request(spec, prompt, temperature, max_tokens=256, seed=0):
    """Return (url, body, headers) for a model spec. Pure, so it is easy to test."""
    provider, _, model = spec.partition("/")
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]
    if provider == "ollama":
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        # think=False turns off qwen3's thinking mode, which otherwise fills the
        # budget with a <think> block before the answer.
        opts = {"temperature": temperature, "num_predict": max_tokens}
        if temperature == 0:
            opts["seed"] = seed  # at temperature > 0 the seed is left random on purpose, see LOGBOOK
        body = {"model": model, "messages": msgs, "stream": False, "think": False, "options": opts}
        return f"{host}/api/chat", body, {}
    if provider in OPENAI_LIKE:
        url, var = OPENAI_LIKE[provider]
        body = {"model": model, "messages": msgs, "temperature": temperature, "max_tokens": max_tokens}
        return url, body, {"Authorization": f"Bearer {_key(var)}"}
    if provider == "anthropic":
        body = {"model": model, "system": SYSTEM, "messages": msgs[1:], "temperature": temperature, "max_tokens": max_tokens}
        return "https://api.anthropic.com/v1/messages", body, {"x-api-key": _key("ANTHROPIC_API_KEY"), "anthropic-version": "2023-06-01"}
    if provider == "gemini":
        body = {"system_instruction": {"parts": [{"text": SYSTEM}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}}
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        return url, body, {"x-goog-api-key": _key("GEMINI_API_KEY")}
    raise ValueError(f"unknown provider in {spec!r}")


def parse_response(spec, data):
    """Pull the text out of a provider response."""
    provider = spec.partition("/")[0]
    if provider == "ollama":
        return data["message"]["content"]
    if provider in OPENAI_LIKE:
        return data["choices"][0]["message"]["content"]
    if provider == "anthropic":
        return "".join(b.get("text", "") for b in data["content"])
    if provider == "gemini":
        return "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
    raise ValueError(spec)


def complete(spec, prompt, temperature=0.0, seed=0, max_tokens=256):
    url, body, headers = build_request(spec, prompt, temperature, max_tokens=max_tokens, seed=seed)
    return parse_response(spec, _post(url, body, headers))
