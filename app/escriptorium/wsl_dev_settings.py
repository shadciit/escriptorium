from escriptorium.settings import *
import os

DEBUG=True
DATABASES['default']['PORT'] = os.getenv('SQL_PORT', '35432')
REDIS_PORT = int(os.getenv('REDIS_PORT', 36379))

CELERY_BROKER_URL = 'redis://%s:%d/0' % (REDIS_HOST, REDIS_PORT)
CELERY_RESULT_BACKEND = 'redis://%s:%d' % (REDIS_HOST, REDIS_PORT)

# CELERY_TASK_ALWAYS_EAGER = True

CACHES['default']['LOCATION'] = "redis://%s:%d/1" % (REDIS_HOST, REDIS_PORT)
LOGGING['handlers']['console']['level'] = 'INFO'

CHANNEL_LAYERS['default']['CONFIG']["hosts"] = [(REDIS_HOST, REDIS_PORT)]
CHANNEL_LAYERS['default']['CONFIG']["capacity"] = 1000