import os
import re
from typing import Any, Dict
from jinja2 import Environment, FileSystemLoader, select_autoescape


class TemplateService:
    """Renders HTML email templates using Jinja2."""

    def __init__(self, templates_dir: str = None):
        if templates_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            templates_dir = os.path.join(os.path.dirname(current_dir), "templates")
        
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(["html", "xml"])
        )

    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render a Jinja2 template with provided context dictionary."""
        template = self.env.get_template(template_name)
        return template.render(**context)

    @staticmethod
    def html_to_plain_text(html_content: str) -> str:
        """Simple plain text extractor from rendered HTML for multipart emails."""
        # Strip script and style tags
        text = re.sub(r"<(script|style).*?>.*?</\1>", "", html_content, flags=re.DOTALL)
        # Replace breaks and paragraphs with newlines
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
        # Strip all remaining tags
        text = re.sub(r"<[^>]+>", "", text)
        # Clean extra whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


_global_template_service = None


def get_template_service() -> TemplateService:
    """Singleton getter for TemplateService."""
    global _global_template_service
    if _global_template_service is None:
        _global_template_service = TemplateService()
    return _global_template_service

