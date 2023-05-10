project = "Opslib"
copyright = "2023, Alex Morega"
author = "Alex Morega"

extensions = [
    "sphinx.ext.intersphinx",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosectionlabel",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "click": ("https://click.palletsprojects.com/en/8.1.x/", None),
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "alabaster"

html_theme_options = {
    "github_user": "mgax",
    "github_repo": "opslib",
}

html_static_path = ["_static"]

autodoc_typehints = "none"
