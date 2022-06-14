from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

import users.routing

from .asgi import application as asgi_app

application = ProtocolTypeRouter({
    'http': asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(
            users.routing.websocket_urlpatterns
        )
    ),
})
