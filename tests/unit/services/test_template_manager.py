"""Tests for TemplateManager built-in templates."""
from __future__ import annotations

from src.services.template_manager import TemplateManager


def test_builtin_templates_available():
    manager = TemplateManager()
    templates = {tmpl.template_id: tmpl for tmpl in manager.available_templates()}

    # Ensure expected templates exist
    assert "backend_feature" in templates
    assert "devops_incident" in templates
    assert "frontend_polish" in templates

    backend = manager.get("backend_feature")
    assert backend is not None
    prompt = backend.build_guideline_prompt()
    assert "Quality" in prompt or prompt  # ensure prompt is generated

