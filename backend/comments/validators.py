import os
from django.core.exceptions import ValidationError
import re
import nh3


ALLOWED_COMMENT_TAGS = {"a", "code", "i", "strong"}
ALLOWED_COMMENT_ATTRIBUTES = {"a": {"href", "title"}}
ALLOWED_COMMENT_URL_SCHEMES = {"http", "https", "mailto"}


def sanitize_comment_html(value):
    return nh3.clean(
        value,
        tags=ALLOWED_COMMENT_TAGS,
        attributes=ALLOWED_COMMENT_ATTRIBUTES,
        url_schemes=ALLOWED_COMMENT_URL_SCHEMES,
        link_rel=None,
        strip_comments=True,
    )


def validate_letters_numbers_only(value):
    """Validate that value contains only letters and numbers."""
    if not re.match(r"^[a-zA-Z0-9]+$", value):
        raise ValidationError(
            "The field can only contain letters and numbers.", code="invalid"
        )


def validate_html_tags(value):
    """Reject markup that would be changed by the comment HTML sanitizer."""
    if sanitize_comment_html(value) != value:
        raise ValidationError(
            "The text contains unsafe or disallowed HTML.",
            code="invalid_html",
        )


MAX_TEXT_FILE_SIZE = 100 * 1024


def validate_txt_file(file):
    if file is None:
        return

    extension = os.path.splitext(file.name)[1].lower()
    if extension != ".txt":
        raise ValidationError("Only .txt files are allowed.")

    if file.size > MAX_TEXT_FILE_SIZE:
        raise ValidationError("Text file size cannot exceed 100 KB.")
