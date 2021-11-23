from django import template


register = template.Library()

@register.simple_tag
def url_replace(request, field, value):
    dict_ = request.GET.copy()
    dict_[field] = value
    return dict_.urlencode()

@register.filter()
def format_tags(tags=None):
    return ('&' + '&'.join([ ('tags=' + tag) for tag in tags])) if tags else ''