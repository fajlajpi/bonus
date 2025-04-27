from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    return value * arg

@register.filter
def dict_get(d, key):
    return d.get(key, 0)

@register.filter
def divide(value, arg):
    return value / arg

@register.filter
def subtract(value, arg):
    """Subtract the arg from the value."""
    return value - arg