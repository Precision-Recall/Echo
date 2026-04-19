"""
Prompt loading system for Echo voice assistant
"""
import os
from pathlib import Path
from typing import Optional

class PromptLoader:
    """Load system prompts from files with fallback support"""
    
    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts_dir = Path(prompts_dir)
        self._ensure_prompts_dir()
    
    def _ensure_prompts_dir(self):
        """Create prompts directory if it doesn't exist"""
        self.prompts_dir.mkdir(exist_ok=True)
    
    def load_prompt(self, filename: str, fallback: Optional[str] = None) -> str:
        """
        Load a prompt file with fallback support
        
        Args:
            filename: Name of prompt file (e.g., "echo_voice.txt")
            fallback: Default prompt if file doesn't exist
            
        Returns:
            Prompt content as string
            
        Raises:
            FileNotFoundError: If file doesn't exist and no fallback provided
        """
        prompt_path = self.prompts_dir / filename
        
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                
            if not content:
                raise ValueError(f"Prompt file {filename} is empty")
                
            return content
            
        except FileNotFoundError:
            if fallback:
                # Create the file with fallback content for future use
                self.save_prompt(filename, fallback)
                return fallback
            raise FileNotFoundError(
                f"Prompt file not found: {prompt_path}\n"
                f"Create it or provide a fallback prompt"
            )
    
    def save_prompt(self, filename: str, content: str):
        """Save prompt content to file"""
        prompt_path = self.prompts_dir / filename
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(content)
    
    def list_prompts(self) -> list[str]:
        """List all available prompt files"""
        return [f.name for f in self.prompts_dir.glob("*.txt")]
    
    def build_dynamic_tool_section(self, connected_mcp_names: list[str]) -> str:
        """
        Build tool context section from connected MCP skill files.
        
        Args:
            connected_mcp_names: list of mcp server keys e.g. ['playwright', 'windows-mcp']
            
        Returns:
            markdown string to inject into system prompt.
        """
        lines = ["## Available Tool Groups", ""]
        skills_dir = self.prompts_dir.parent / "mcp_skills"
        
        for name in connected_mcp_names:
            skill_file = skills_dir / f"{name}.md"
            if skill_file.exists():
                content = skill_file.read_text(encoding="utf-8").strip()
                # Parse name: and abstract: lines
                parsed = {}
                for line in content.splitlines():
                    if line.startswith("name:"):
                        parsed["name"] = line.split(":", 1)[1].strip()
                    elif line.startswith("abstract:"):
                        parsed["abstract"] = line.split(":", 1)[1].strip()
                if "name" in parsed and "abstract" in parsed:
                    lines.append(f"- **{parsed['name']}**: {parsed['abstract']}")
            else:
                # Fallback: just list the server name
                lines.append(f"- **{name}**: MCP server (no skill file found)")
        
        lines += ["", "Use tool group name as hint when selecting tools. Full tool list injected by runtime."]
        return "\n".join(lines)
