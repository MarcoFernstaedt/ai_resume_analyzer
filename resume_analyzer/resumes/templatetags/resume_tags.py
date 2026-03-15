from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get dict item by key in templates."""
    if isinstance(dictionary, dict):
        return dictionary.get(key, 0)
    return 0

@register.filter
def split(value, delimiter=','):
    return value.split(delimiter)
