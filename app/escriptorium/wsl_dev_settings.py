from escriptorium.settings import *

DEBUG=True
DATABASES['default']['PORT'] = os.getenv('SQL_PORT', '35432')
REDIS_PORT = int(os.getenv('REDIS_PORT', 36379))

CELERY_BROKER_URL = 'redis://%s:%d/0' % (REDIS_HOST, REDIS_PORT)
CELERY_RESULT_BACKEND = 'redis://%s:%d' % (REDIS_HOST, REDIS_PORT)
CELERY_TASK_ALWAYS_EAGER = True

LOGGING['handlers']['console']['level'] = 'INFO'
