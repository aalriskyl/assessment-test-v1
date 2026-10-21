"""Check the configured model with synthetic text, without sending a document."""

import json
import os
import re
import sys
import time
from pathlib import Path

import requests


def main() -> int:
    key = os.environ.get("GEMINI_API_KEY", "")
    requested = os.environ.get("AI_MODEL", "")
    report: dict[str, object] = {"requested_model": requested}
    try:
        if not key or not re.fullmatch(r"gemini-[A-Za-z0-9._-]{1,100}", requested):
            raise ValueError("Missing key or invalid model")
        payload = {
            "model": requested,
            "store": False,
            "input": "Return ready as true.",
            "response_format": {
                "type": "text",
                "mime_type": "application/json",
                "schema": {
                    "type": "object",
                    "properties": {"ready": {"type": "boolean"}},
                    "required": ["ready"],
                    "additionalProperties": False,
                },
            },
            "generation_config": {"max_output_tokens": 512},
        }
        for attempt in range(2):
            response = requests.post(
                "https://generativelanguage.googleapis.com/v1/interactions",
                headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                json=payload,
                timeout=(5, 30),
                allow_redirects=False,
            )
            if response.status_code != 503 or attempt == 1:
                break
            time.sleep(1)
        report["http_status"] = response.status_code
        result = response.json()
        if not response.ok:
            # Only this synthetic probe's error is saved; never supplier data or credentials.
            message = str(result.get("error", {}).get("message", "Request rejected"))
            report["error"] = message.replace(key, "[redacted]")[:700]
            if response.status_code in {429, 503}:
                # Temporary capacity/quota failures should not disable local/manual entry.
                report["selected_model"] = requested
        else:
            text = "".join(
                part["text"]
                for step in result.get("steps", [])
                if step.get("type") == "model_output"
                for part in step.get("content", [])
                if part.get("type") == "text"
            )
            if result.get("status") != "completed" or json.loads(text) != {"ready": True}:
                raise ValueError("Incomplete or invalid probe")
            report["selected_model"] = requested
    except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError):
        report["error"] = "Gemini check failed. Check the key, model and connectivity, then retry."
    target = Path(__file__).resolve().parents[1] / "instance/gemini-preflight.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if "selected_model" not in report:
        print("Gemini preflight failed:", report["error"])
        print("Safe diagnostic report:", target)
        return 1
    print("Gemini model:", report["selected_model"])
    if "error" in report:
        print("Provider not ready:", report["error"])
        print("Starting with local/manual input available; AI extraction may need a later retry.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
