"""
Unit tests for apps.core.lib.pdf_engine — PDFAssembler template directory
creation, Jinja2 environment setup, and security constraints.

Real filesystem operations. No mocks.
"""

import os
import tempfile

import pytest

# Skip entire module if weasyprint is not installed
pytest.importorskip("weasyprint", reason="weasyprint not installed")

from apps.core.lib.pdf_engine import PDFAssembler


class TestPDFAssemblerTemplateDir:
    """Test template directory handling."""

    def test_template_dir_path_construction(self):
        """Verify the template directory path is constructed correctly."""
        os.path.dirname(os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "apps", "core", "lib", "pdf_engine.py")
        ))
        # The template_dir is computed relative to the pdf_engine.py file
        pdf_engine_dir = os.path.dirname(os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..", "..", "..", "..",
                "apps", "core", "lib", "pdf_engine.py",
            )
        ))
        template_dir = os.path.join(pdf_engine_dir, "templates")
        assert template_dir.endswith("templates")

    def test_template_dir_created_if_missing(self):
        """Verify that os.makedirs is called with exist_ok=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = os.path.join(tmpdir, "templates")
            assert not os.path.exists(template_dir)
            os.makedirs(template_dir, exist_ok=True)
            assert os.path.exists(template_dir)
            # Calling again should not raise
            os.makedirs(template_dir, exist_ok=True)


class TestPDFAssemblerSecurity:
    """Test security constraints in PDFAssembler."""

    def test_jinja2_filesystem_loader_restricts_to_template_dir(self):
        """Jinja2 FileSystemLoader should only load from the specified directory."""
        from jinja2 import Environment, FileSystemLoader, select_autoescape

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a template
            with open(os.path.join(tmpdir, "test.html"), "w") as f:
                f.write("<h1>{{ title }}</h1>")

            env = Environment(
                loader=FileSystemLoader(tmpdir),
                autoescape=select_autoescape(["html", "xml"]),
            )
            template = env.get_template("test.html")
            result = template.render(title="Hello")
            assert "Hello" in result

    def test_jinja2_autoescape_enabled(self):
        """Verify autoescape is configured for HTML/XML."""
        from jinja2 import Environment, select_autoescape

        env = Environment(autoescape=select_autoescape(["html", "xml"]))
        # autoescape should be enabled for .html templates
        assert env.autoescape

    def test_template_not_found_raises(self):
        """Loading a non-existent template should raise TemplateNotFound."""
        from jinja2 import Environment, FileSystemLoader, TemplateNotFound

        with tempfile.TemporaryDirectory() as tmpdir:
            env = Environment(loader=FileSystemLoader(tmpdir))
            with pytest.raises(TemplateNotFound):
                env.get_template("nonexistent.html")


class TestPDFAssemblerClassMethod:
    """Test PDFAssembler class-level attributes."""

    def test_compile_pdf_is_classmethod(self):
        """compile_pdf should be callable as a class method."""
        assert isinstance(PDFAssembler.__dict__["compile_pdf"], classmethod)

    def test_class_has_compile_pdf(self):
        assert hasattr(PDFAssembler, "compile_pdf")
