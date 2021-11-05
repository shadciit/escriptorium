from django import template


register = template.Library()

@register.filter()
def select_key(obj, key):
    return obj[key]
