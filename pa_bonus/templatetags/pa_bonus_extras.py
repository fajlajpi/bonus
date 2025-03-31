from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    return value * arg

@register.filter
def dict_get(d, key):
    return d.get(key, 0)