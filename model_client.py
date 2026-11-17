"""
model_client.py - talks to the language model.

Owner: Swathi (agent)

Default: a local model through Ollama (same setup as earlier homework).
Settings (environment variables, all optional):
    LOAN_AGENT_MODEL   model name            (default: qwen3:8b)
    OLLAMA_URL         Ollama server address (default: http://localhost:11434)
    LOAN_AGENT_THINK   1 = let Qwen3 "think" before answering, 0 = off (default 0)

No extra Python packages are needed; this uses the standard library.
"""

import http.client
import json
import os
import re
import urllib.error
import urllib.request

MODEL = os.environ.get("LOAN_AGENT_MODEL", "qwen3:8b")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
THINK = os.environ.get("LOAN_AGENT_THINK", "0") == "1"


def strip_think_tags(text):
    return re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL).strip()


def call_ollama(messages, tools):
    """Send the conversation to Ollama. Returns a simple dictionary:
        content     - any text the model wrote
        tool_calls  - list of {"name": ..., "arguments": {...}}
        raw_message - the model's message, to put back into the conversation
        usage       - token counts and time reported by Ollama
    """
    body = {
        "model": MODEL,
        "messages": messages,
        "tools": tools,
        "stream": False,
        "think": THINK,
        "options": {"temperature": 0},  # makes runs as repeatable as possible
    }
    request = urllib.request.Request(
        OLLAMA_URL + "/api/chat",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Ollama answered but refused, e.g. the model does not support tools.
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError("Ollama returned HTTP %s: %s" % (exc.code, detail))
    except (urllib.error.URLError, http.client.HTTPException, OSError) as exc:
        raise RuntimeError(
            "Could not reach Ollama at %s (%s). Is 'ollama serve' running and is the "
            "model pulled? Try: ollama pull %s" % (OLLAMA_URL, exc, MODEL)
        )

    message = data.get("message", {})
    tool_calls = []
    for call in message.get("tool_calls") or []:
        function = call.get("function", {})
        arguments = function.get("arguments", {})
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except ValueError:
                arguments = {"_unparsed": arguments}
        tool_calls.append({"name": function.get("name"), "arguments": arguments})

    return {
        "content": strip_think_tags(message.get("content", "")),
        "thinking": message.get("thinking", ""),
        "tool_calls": tool_calls,
        "raw_message": message,
        "usage": {
            "prompt_tokens": data.get("prompt_eval_count", 0),
            "output_tokens": data.get("eval_count", 0),
            "model_seconds": round(data.get("total_duration", 0) / 1e9, 2),
        },
    }


def model_description():
    return "%s via Ollama (temperature 0, think=%s)" % (MODEL, THINK)
