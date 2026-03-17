#!/usr/bin/env python3
"""Validate all RainGod API keys by hitting each service's health endpoint."""

import asyncio
import os
import sys
import httpx

CHECKS = {
    "OLLAMA_HOST": {
        "label": "Ollama (local)",
        "fn": lambda: _check_ollama(),
    },
    "GROQ_API_KEY": {
        "label": "Groq",
        "fn": lambda: _check_groq(),
    },
    "GEMINI_API_KEY": {
        "label": "Google Gemini",
        "fn": lambda: _check_gemini(),
    },
    "COMFY_API_KEY": {
        "label": "Comfy Cloud",
        "fn": lambda: _check_comfy_cloud(),
    },
    "OPENROUTER_API_KEY": {
        "label": "OpenRouter",
        "fn": lambda: _check_openrouter(),
    },
    "HF_TOKEN": {
        "label": "HuggingFace",
        "fn": lambda: _check_hf(),
    },
    "SUNO_API_KEY": {
        "label": "Suno",
        "fn": lambda: _check_suno(),
    },
    "REPLICATE_API_KEY": {
        "label": "Replicate",
        "fn": lambda: _check_replicate(),
    },
}


async def _check_ollama() -> tuple[bool, str]:
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(f"{host}/api/tags")
            models = [m["name"] for m in r.json().get("models", [])]
            return True, f"{len(models)} models: {', '.join(models[:4])}"
    except Exception as e:
        return False, str(e)


async def _check_groq() -> tuple[bool, str]:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        return False, "NOT SET"
    try:
        async with httpx.AsyncClient(
            headers={"Authorization": f"Bearer {key}"}, timeout=10
        ) as c:
            r = await c.get("https://api.groq.com/openai/v1/models")
            count = len(r.json().get("data", []))
            return True, f"{count} models available"
    except Exception as e:
        return False, str(e)


async def _check_gemini() -> tuple[bool, str]:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return False, "NOT SET"
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
            )
            r.raise_for_status()
            return True, "key valid"
    except Exception as e:
        return False, str(e)


async def _check_comfy_cloud() -> tuple[bool, str]:
    key = os.getenv("COMFY_API_KEY")
    if not key:
        return False, "NOT SET"
    try:
        async with httpx.AsyncClient(
            headers={"Authorization": f"Bearer {key}"}, timeout=10
        ) as c:
            r = await c.get("https://api.comfy.org/v1/user")
            if r.status_code == 200:
                data = r.json()
                credits = data.get("credits", "?")
                return True, f"credits: {credits}"
            return False, f"HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)


async def _check_openrouter() -> tuple[bool, str]:
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        return False, "NOT SET"
    try:
        async with httpx.AsyncClient(
            headers={"Authorization": f"Bearer {key}"}, timeout=10
        ) as c:
            r = await c.get("https://openrouter.ai/api/v1/models")
            count = len(r.json().get("data", []))
            return True, f"{count} models available"
    except Exception as e:
        return False, str(e)


async def _check_hf() -> tuple[bool, str]:
    token = os.getenv("HF_TOKEN")
    if not token:
        return False, "NOT SET"
    try:
        async with httpx.AsyncClient(
            headers={"Authorization": f"Bearer {token}"}, timeout=10
        ) as c:
            r = await c.get("https://huggingface.co/api/whoami-v2")
            if r.status_code == 200:
                name = r.json().get("name", "?")
                return True, f"logged in as: {name}"
            return False, f"HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)


async def _check_suno() -> tuple[bool, str]:
    key = os.getenv("SUNO_API_KEY")
    if not key:
        return False, "NOT SET"
    return True, "key present (Suno has no lightweight ping endpoint)"


async def _check_replicate() -> tuple[bool, str]:
    key = os.getenv("REPLICATE_API_KEY")
    if not key:
        return False, "NOT SET"
    try:
        async with httpx.AsyncClient(
            headers={"Authorization": f"Token {key}"}, timeout=10
        ) as c:
            r = await c.get("https://api.replicate.com/v1/account")
            if r.status_code == 200:
                name = r.json().get("username", "?")
                return True, f"account: {name}"
            return False, f"HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)


async def main() -> None:
    # Load .env if present
    env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    if v and not os.getenv(k.strip()):
                        os.environ[k.strip()] = v.strip()

    print("\n🔍 RainGod API Key Validation\n" + "─" * 45)
    all_ok = True
    for env_key, meta in CHECKS.items():
        ok, detail = await meta["fn"]()
        icon = "✅" if ok else "❌"
        print(f"  {icon}  {meta['label']:<20} {detail}")
        if not ok and env_key not in ("REPLICATE_API_KEY",):
            all_ok = False

    print("─" * 45)
    if all_ok:
        print("✅ All core services validated. RainGod fleet is ready.\n")
    else:
        print("⚠️  Some services missing. Run scripts/deploy_api_keys.ps1 to add keys.\n")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
