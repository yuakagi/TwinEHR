from django import template
from django.forms.boundfield import BoundField

register = template.Library()


@register.filter
def widget_class_name(field):
    if not isinstance(field, BoundField):
        print(field)
        return ""
    return field.field.widget.__class__.__name__
