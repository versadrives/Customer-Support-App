from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def add_class(value, css_class):
    """
    Adds CSS class to form field widget.
    Usage: {{ form.field|add_class:"my-class" }}
    """
    if hasattr(value, 'field') and value.field.widget.attrs is not None:
        attrs = value.field.widget.attrs.copy()
        current_class = attrs.get('class', '')
        attrs['class'] = f"{current_class} {css_class}".strip()
        value.field.widget.attrs = attrs
    return value

