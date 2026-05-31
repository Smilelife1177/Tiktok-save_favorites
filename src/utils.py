# Utils can be added here as the project grows
def sanitize_filename(name):
    """Simple utility to sanitize filenames if needed."""
    return "".join([c for c in name if c.isalpha() or c.isdigit() or c in ' ._-']).strip()
