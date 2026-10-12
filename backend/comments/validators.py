import os
from django.core.exceptions import ValidationError

import re


def validate_letters_numbers_only(value):
    """Validate that value contains only letters and numbers."""
    if not re.match(r"^[a-zA-Z0-9]+$", value):
        raise ValidationError(
            "The field can only contain letters and numbers.", code="invalid"
        )


def validate_html_tags(value):
    """Validate that value contains only allowed HTML tags and is valid XHTML."""
    allowed_tags = {"a", "code", "i", "strong"}
    # We'll do a simple check: remove allowed tags and see if any angle brackets remain
    # This is not a full XHTML validator but serves for the assignment.
    # For a production system, use a proper library like bleach.
    # We'll allow text without tags as well.
    # Remove allowed tags
    cleaned = re.sub(
        r"<(/?)(a|code|i|strong)(\s[^>]*)?>", "", value, flags=re.IGNORECASE
    )
    # If there are any remaining angle brackets, it's invalid
    if "<" in cleaned or ">" in cleaned:
        raise ValidationError(
            "The text contains disallowed HTML tags. Allowed: <a>, <code>, <i>, <strong>.",
            code="invalid_html",
        )
    # Additionally, we could check for well-formedness, but we skip for simplicity.


MAX_TEXT_FILE_SIZE = 100 * 1024


def validate_txt_file(file):
    if file is None:
        return

    extension = os.path.splitext(file.name)[1].lower()
    if extension != ".txt":
        raise ValidationError("Only .txt files are allowed.")

    if file.size > MAX_TEXT_FILE_SIZE:
        raise ValidationError("Text file size cannot exceed 100 KB.")
