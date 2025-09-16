import os
import requests
import logging
from dotenv import load_dotenv
from pathlib import Path
import time
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
import json
import re
import asyncio
import aiohttp
from typing import Dict, List, Optional, Generator, AsyncGenerator, Any
import subprocess
import sys

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
    "HTTP-Referer": "https://github.com/yourusername/pysprit",
    "X-Title": "PySprit"
}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("pysprit.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("pysprit")

console = Console()

class AIAssistant:
    """Handles all AI interactions with robust error handling and retries."""
    
    def __init__(self, api_url: str, headers: Dict[str, str], model: str):
        self.api_url = api_url
        self.headers = headers
        self.model = model
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def ask_ai(self, prompt: str, system_prompt: str, stream: bool = False) -> Optional[str]:
        """Send request to AI with retry logic."""
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                data = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "stream": stream
                }
                
                if stream:
                    return await self._stream_response(data)
                else:
                    return await self._get_response(data)
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning(f"AI request attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
                else:
                    logger.error(f"All AI request attempts failed: {e}")
                    return None
    
    async def _get_response(self, data: Dict[str, Any]) -> Optional[str]:
        """Get non-streaming response from AI."""
        async with self.session.post(self.api_url, headers=self.headers, json=data) as resp:
            resp.raise_for_status()
            result = await resp.json()
            return result["choices"][0]["message"]["content"]
    
    async def _stream_response(self, data: Dict[str, Any]) -> str:
        """Stream AI response and display it in real-time."""
        full_output = ""
        
        async with self.session.post(self.api_url, headers=self.headers, json=data) as resp:
            resp.raise_for_status()
            
            console.print("[cyan]--- AI Writing Code ---[/cyan]")
            
            async for line in resp.content:
                if line:
                    try:
                        decoded_line = line.decode('utf-8').strip()
                        if decoded_line.startswith("data: "):
                            payload = json.loads(decoded_line[len("data: "):])
                            delta = payload.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if delta:
                                console.print(delta, end="", style="green")
                                full_output += delta
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        logger.warning(f"Error parsing streaming response: {e}")
                        continue
        
        console.print("\n[cyan]--- Done ---[/cyan]")
        return full_output


class JSONProcessor:
    """Handles JSON processing with robust error recovery."""
    
    @staticmethod
    def extract_json_from_text(text: str) -> str:
        """Extract JSON from text that might contain other content."""
        if not text:
            return "{}"
        
        # Try to find JSON objects/arrays using regex
        json_patterns = [
            r'(\{.*\})',  # JSON object
            r'(\[.*\])',  # JSON array
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                try:
                    json.loads(match)
                    return match
                except json.JSONDecodeError:
                    continue
        
        return "{}"
    
    @staticmethod
    def clean_ai_output(output: str) -> str:
        """Remove markdown fences and trim, then extract JSON."""
        if not output:
            return "{}"
        
        # Remove markdown code fences
        output = re.sub(r"^```[a-zA-Z0-9]*\s*", "", output.strip())
        output = re.sub(r"```$", "", output.strip())
        
        # Try to extract JSON from the text
        return JSONProcessor.extract_json_from_text(output)
    
    @staticmethod
    def robust_json_parse(json_str: str, max_attempts: int = 3) -> Dict:
        """Attempt to parse JSON with multiple repair strategies."""
        if not json_str or json_str.strip() == "":
            return {}
        
        json_str = json_str.strip()
        
        # Attempt 1: Direct parsing
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse attempt 1 failed: {e}")
        
        # Attempt 2: Remove trailing commas
        try:
            repaired = re.sub(r",\s*([\]}])", r"\1", json_str)
            return json.loads(repaired)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse attempt 2 failed: {e}")
        
        # Attempt 3: Fix common issues
        try:
            repaired = re.sub(r"(?<!\\)'", '"', json_str)
            repaired = re.sub(r'(?<!\\)"', '\\"', repaired)
            repaired = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', repaired)
            return json.loads(repaired)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse attempt 3 failed: {e}")
        
        # Final attempt: Extract the largest valid JSON object
        try:
            brace_count = 0
            start_index = -1
            best_candidate = ""
            
            for i, char in enumerate(json_str):
                if char == '{':
                    if brace_count == 0:
                        start_index = i
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and start_index != -1:
                        candidate = json_str[start_index:i+1]
                        try:
                            json.loads(candidate)
                            if len(candidate) > len(best_candidate):
                                best_candidate = candidate
                        except json.JSONDecodeError:
                            pass
            
            if best_candidate:
                return json.loads(best_candidate)
        except json.JSONDecodeError as e:
            logger.warning(f"Final JSON parse attempt failed: {e}")
        
        logger.error("All JSON parsing attempts failed")
        return {}


class ProjectGenerator:
    """Main class for generating projects with AI assistance."""
    
    def __init__(self, ai_assistant: AIAssistant, json_processor: JSONProcessor):
        self.ai = ai_assistant
        self.json_processor = json_processor
        
    async def generate_project(self, task: str, output_dir: Path) -> Generator[str, None, None]:
        """Main project generation function with enhanced JSON handling."""
        system_prompt_path = Path("SYSTEM_PROMPT.md")
        if not system_prompt_path.exists():
            yield "❌ Missing SYSTEM_PROMPT.md"
            return

        base_system_prompt = system_prompt_path.read_text(encoding="utf-8")
        
        # Enhanced JSON rules with examples
        json_rules = """
IMPORTANT JSON OUTPUT RULES FOR PROJECT GENERATION:
1. Your ENTIRE response must be ONLY valid JSON - no additional text before or after.
2. Do NOT use markdown code fences (```json) or any other formatting.
3. The JSON structure must follow this exact format:
   {
     "path/to/file1.ext": "file content here",
     "path/to/file2.ext": "file content here",
     "path/to/file3.ext": "file content here"
   }
4. Ensure:
   - All strings use double quotes (not single quotes)
   - No trailing commas in arrays or objects
   - Proper escaping of special characters in file content
   - Valid JSON structure with matching braces/brackets
5. Example of valid output:
   {"src/main.py": "print('Hello World')", "README.md": "# My Project"}
6. If you cannot generate the project, output an empty object: {}
"""
        
        system_prompt = base_system_prompt + "\n" + json_rules
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="🤖 Generating project...", total=None)
            
            project_code = await self.ai.ask_ai(
                f"Generate all files for this project: '{task}'. "
                f"Output ONLY valid JSON in the format {{'file/path': 'file content'}}. "
                f"Ensure the JSON is valid and contains no extra text.",
                system_prompt,
                stream=True
            )
        
        if not project_code:
            yield "❌ No AI output"
            return

        # Enhanced cleaning and parsing
        cleaned = self.json_processor.clean_ai_output(project_code)
        logger.info(f"Cleaned output: {cleaned[:200]}...")

        # Try to parse the JSON with multiple strategies
        files = self.json_processor.robust_json_parse(cleaned)
        
        # If parsing failed, try AI repair
        if not files:
            files = await self._repair_json_with_ai(cleaned)
        
        # If still no files, create a default structure
        if not files:
            logger.warning("Using fallback project structure")
            files = {
                "src/main.py": "# Your project code here\nprint('Hello World')",
                "README.md": f"# {task}\n\nProject generated by PySprit",
                "requirements.txt": "# Project dependencies"
            }

        # Write files
        for rel_path, content in files.items():
            file_path = output_dir / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            yield f"✅ Generated: {file_path}"
            await asyncio.sleep(0.1)  # Small delay to prevent rate limiting

        yield f"✨ Project ready in '{output_dir}'"
        
        # Try to set up the project
        async for message in self._setup_project(output_dir):
            yield message
    
    async def _repair_json_with_ai(self, broken_json: str) -> Dict:
        """Ask AI to fix malformed JSON."""
        logger.warning("JSON parsing failed — asking AI to repair...")
        system_prompt = """You are a JSON repair assistant. 
        Fix the following broken JSON and output ONLY valid JSON with no additional text.
        Ensure:
        1. All strings use double quotes
        2. No trailing commas in arrays or objects
        3. Proper escaping of special characters
        4. Valid JSON structure
        """
        fixed = await self.ai.ask_ai(f"Fix this broken JSON:\n\n{broken_json}", system_prompt)
        if fixed:
            fixed_clean = self.json_processor.clean_ai_output(fixed)
            try:
                return json.loads(fixed_clean)
            except json.JSONDecodeError as e:
                logger.error(f"AI JSON repair failed: {e}")
        return {}
    
    async def _setup_project(self, output_dir: Path) -> AsyncGenerator[str, None]:
        """Attempt to set up the generated project."""
        # Check if requirements.txt exists and install dependencies
        requirements_file = output_dir / "requirements.txt"
        if requirements_file.exists():
            try:
                yield "📦 Installing dependencies..."
                result = await asyncio.create_subprocess_exec(
                    sys.executable, "-m", "pip", "install", "-r", str(requirements_file),
                    cwd=output_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await result.communicate()
                if result.returncode == 0:
                    yield "✅ Dependencies installed successfully"
                else:
                    yield f"⚠ Failed to install dependencies: {result.stderr}"
            except subprocess.TimeoutExpired:
                yield "⚠ Dependency installation timed out"
            except Exception as e:
                yield f"⚠ Error installing dependencies: {e}"
        
        # Check if setup.py exists and try to install the package
        setup_file = output_dir / "setup.py"
        if setup_file.exists():
            try:
                yield "🔧 Installing package in development mode..."
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-e", "."],
                    cwd=output_dir,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                if result.returncode == 0:
                    yield "✅ Package installed successfully"
                else:
                    yield f"⚠ Failed to install package: {result.stderr}"
            except subprocess.TimeoutExpired:
                yield "⚠ Package installation timed out"
            except Exception as e:
                yield f"⚠ Error installing package: {e}"


async def main():
    """Main function to run the project generator."""
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
    else:
        task = console.input("💬 Project description: ").strip()
    
    if not task:
        console.print("❌ No project description provided", style="red")
        return
    
    output_dir = Path("generated_code") / re.sub(r'[^\w\-_\. ]', '_', task)[:50]
    
    # Initialize components
    json_processor = JSONProcessor()
    
    async with AIAssistant(API_URL, HEADERS, MODEL_NAME) as ai_assistant:
        generator = ProjectGenerator(ai_assistant, json_processor)
        
        async for msg in generator.generate_project(task, output_dir):
            console.print(msg)


if __name__ == "__main__":
    asyncio.run(main())