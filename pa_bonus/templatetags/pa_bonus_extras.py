from django import template
import datetime

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

@register.filter
def sum_attr(items, attr_name):
    """Calculate the sum of a specific attribute across a list of dictionaries."""
    try:
        return sum(item[attr_name] for item in items)
    except (KeyError, TypeError):
        return 0

@register.filter
def range_loop(value):
    """Create a range from 1 to value."""
    try:
        return range(1, int(value) + 1)
    except (ValueError, TypeError):
        return range(1)

@register.simple_tag
def year_range(start_year, end_year):
    """Create a list of years from start_year to end_year (inclusive)."""
    try:
        start = int(start_year)
        end = int(end_year) + 1
        return range(start, end)
    except (ValueError, TypeError):
        current_year = datetime.datetime.now().year
        return range(current_year - 5, current_year + 1)