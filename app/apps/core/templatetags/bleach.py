import bleach

from django import template


register = template.Library()

@register.filter
def strip_html(obj, tags=None):
    tags = tags or None
    return bleach.clean(obj, strip=True, tags=tags)

@register.filter()
def format_tags(tags=None):
    return ('&' + '&'.join([ ('tags=' + tag) for tag in tags])) if tags else ''