import json

from django import template


register = template.Library()

@register.filter
def jsond(obj):
    return json.dumps(obj)

@register.filter
def parsedict(obj):
    list_data = [v for k,v in obj.items()]
    return list_data