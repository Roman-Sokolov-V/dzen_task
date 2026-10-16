import os
import django
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from comments.routing import websocket_urlpatterns

print("Routes:")
for pattern in websocket_urlpatterns:
    print(f"  {pattern}")
    # Get the regex pattern string
    regex_pattern = pattern.pattern.regex.pattern
    print(f"  Regex pattern: {regex_pattern}")

    # Test matching
    test_paths = [
        '/ws/comments/',
        'ws/comments/',
        '/ws/comments',
        'ws/comments',
    ]

    for path in test_paths:
        match = re.fullmatch(regex_pattern, path)
        print(f"    Path '{path}' matches: {match is not None}")