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
