# attachments/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Template filter to get dictionary item by key"""
    return dictionary.get(key, [])


@register.filter
def basename(value):
    """Get the basename of a file path"""
    import os
    return os.path.basename(value)