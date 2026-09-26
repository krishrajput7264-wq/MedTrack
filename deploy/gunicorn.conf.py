import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
timeout = 120
keepalive = 5
accesslog = "/home/ec2-user/medtrack/logs/gunicorn-access.log"
errorlog = "/home/ec2-user/medtrack/logs/gunicorn-error.log"
capture_output = True
loglevel = "info"
