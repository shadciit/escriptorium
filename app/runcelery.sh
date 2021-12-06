#celery -A escriptorium worker -P eventlet -c 100 -l INFO
celery -A escriptorium worker -c 8 -l INFO
