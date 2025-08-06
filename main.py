import os
import requests
import logging
from dotenv import load_dotenv
from pathlib import Path
import time
from rich.console import Console
import json
import re

# Load API key
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY is not set. Add it in .env.")

# Constants
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "z-ai/glm-4.5-air:free"
HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://github.com/yourusername/yourproject",
    "X-Title": "PySprit"
}

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
console = Console()

# ---------------- Utility Functions ---------------- #

def clean_ai_output(output: str) -> str:
    """Remove markdown fences and trim."""
    output = re.sub(r"^```[a-zA-Z0-9]*\s*", "", output.strip())
    output = re.sub(r"```$", "", output.strip())
    return output.strip()

def local_json_repair(broken_json: str) -> str:
    """Fix common JSON issues locally."""
    repaired = broken_json.strip()
    repaired = re.sub(r",\s*([\]}])", r"\1", repaired)  # remove trailing commas
    repaired = re.sub(r"(?<!\\)'", '"', repaired)       # convert single to double quotes
    if not repaired.startswith("{") and not repaired.startswith("["):
        repaired = "{" + repaired
    if not repaired.endswith("}") and not repaired.endswith("]"):
        repaired += "}"
    return repaired

def ask_ai(prompt: str, system_prompt: str) -> str:
    """Send request to AI (non-stream)."""
    data = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    }
    try:
        resp = requests.post(API_URL, headers=HEADERS, json=data, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        console.print(f"❌ AI request failed: {e}", style="red")
        return None

def ask_ai_stream(prompt: str, system_prompt: str) -> str:
    """Stream AI output live to the console."""
    data = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "stream": True
    }
    try:
        with requests.post(API_URL, headers=HEADERS, json=data, stream=True) as resp:
            resp.raise_for_status()
            console.print("[cyan]--- AI Writing Code ---[/cyan]")
            full_output = ""
            for line in resp.iter_lines(decode_unicode=True):
                if line and line.strip() != "":
                    try:
                        if line.startswith("data: "):
                            payload = json.loads(line[len("data: "):])
                            delta = payload.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if delta:
                                print(delta, end="", flush=True)  # live typing
                                full_output += delta
                    except Exception:
                        pass
            print("\n[cyan]--- Done ---[/cyan]")
            return full_output
    except Exception as e:
        console.print(f"❌ Streaming error: {e}", style="red")
        return None

def repair_json_with_ai(broken_json: str) -> dict:
    """Ask AI to fix malformed JSON."""
    console.print("⚠ JSON parsing failed — asking AI to repair...", style="yellow")
    system_prompt = "You are a JSON repair assistant. Output ONLY valid JSON — no explanations."
    fixed = ask_ai(f"Fix this broken JSON so it's valid:\n\n{broken_json}", system_prompt)
    if fixed:
        fixed_clean = clean_ai_output(fixed)
        try:
            return json.loads(fixed_clean)
        except json.JSONDecodeError as e:
            console.print(f"❌ JSON repair failed: {e}", style="red")
    return None

# ---------------- Main Project Generator ---------------- #

def generate_project_with_progress(task: str):
    """Main project generation function with JSON rules injection."""
    system_prompt_path = Path("SYSTEM_PROMPT.md")
    if not system_prompt_path.exists():
        yield "❌ Missing SYSTEM_PROMPT.md"
        return

    base_system_prompt = system_prompt_path.read_text(encoding="utf-8")
    json_rules = """
IMPORTANT JSON OUTPUT RULES FOR PROJECT GENERATION:
1. When generating a project, your ENTIRE response must be ONLY valid JSON.
2. Do not include explanations, markdown code fences, or comments outside the JSON.
3. The JSON structure must be:
   {
     "path/to/file1.ext": "file content here",
     "path/to/file2.ext": "file content here"
   }
4. Always ensure matching braces/brackets and proper escaping of quotes/newlines in values.
5. Do not stream partial JSON objects — always output fully valid JSON.
6. If unsure, output {}.
"""
    system_prompt = base_system_prompt + "\n" + json_rules

    output_dir = Path("generated_code") / "hibye"
    yield "🤖 Generating project..."

    project_code = ask_ai_stream(
        f"Generate all files for this project: '{task}'. "
        f"Output ONLY valid JSON in the format {{'file/path': 'file content'}}. "
        f"Ensure the JSON is valid and contains no extra text.",
        system_prompt
    )
    if not project_code:
        yield "❌ No AI output"
        return

    cleaned = clean_ai_output(project_code)

    # Hybrid repair system
    try:
        files = json.loads(cleaned)
    except json.JSONDecodeError:
        files = repair_json_with_ai(cleaned)
        if not files:
            console.print("⚠ AI repair failed — attempting local repair...", style="yellow")
            repaired_json = local_json_repair(cleaned)
            try:
                files = json.loads(repaired_json)
                console.print("✅ Local JSON repair successful!", style="green")
            except json.JSONDecodeError as e:
                yield f"❌ Could not fix JSON after AI + local repair. Error: {e}"
                return

    # Write files
    for rel_path, content in files.items():
        file_path = output_dir / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        yield f"✅ Generated: {file_path}"
        time.sleep(0.2)

    yield f"✨ Project ready in '{output_dir}'"

# ---------------- Run Script ---------------- #

if __name__ == "__main__":
    import sys
    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("💬 Project description: ").strip()
    for msg in generate_project_with_progress(task):
        console.print(msg)
