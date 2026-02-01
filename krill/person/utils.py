"""
Shared utilities for the person app.
"""

import os
import tempfile


def get_upload_temp_dir():
    """
    Return the resolved absolute path for temporary file uploads.
    Uses Django's FILE_UPLOAD_TEMP_DIR if set, otherwise the system temp directory.
    """
    from django.conf import settings

    temp_dir = getattr(settings, 'FILE_UPLOAD_TEMP_DIR', None) or tempfile.gettempdir()
    return os.path.abspath(os.path.expanduser(str(temp_dir)))
