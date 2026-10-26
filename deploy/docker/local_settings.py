import os
from urllib.parse import urlparse


def _env_bool(name, default=False):
    return os.getenv(name, str(default)).lower() in {'1', 'true', 'yes', 'on'}


def _env_list(name, default=''):
    return [item.strip() for item in os.getenv(name, default).split(',') if item.strip()]


FRONTEND_HOST = os.getenv('FRONTEND_HOST', 'http://localhost')
PORTAL_NAME = os.getenv('PORTAL_NAME', 'MediaCMS')
REDIS_LOCATION = os.getenv('REDIS_LOCATION', 'redis://redis:6379/1')

# ALLOWED_HOSTS keeps the project defaults from cms/settings.py unless the operator
# restricts it explicitly, so existing deployments accessed through other hostnames
# (or the server IP) keep working.
_allowed_hosts = _env_list('ALLOWED_HOSTS')
if _allowed_hosts:
    ALLOWED_HOSTS = _allowed_hosts
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv('POSTGRES_NAME', 'mediacms'),
        "HOST": os.getenv('POSTGRES_HOST', 'db'),
        "PORT": os.getenv('POSTGRES_PORT', '5432'),
        "USER": os.getenv('POSTGRES_USER', 'mediacms'),
        "PASSWORD": os.getenv('POSTGRES_PASSWORD', 'mediacms'),
        "OPTIONS": {
            "pool": {
                "min_size": 2,
                "max_size": 8,
                "timeout": 10,
                "max_lifetime": 30 * 60,
                "max_idle": 10 * 60,
            }
        },
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_LOCATION,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

# CELERY STUFF
BROKER_URL = REDIS_LOCATION
CELERY_RESULT_BACKEND = BROKER_URL

MP4HLS_COMMAND = "/home/mediacms.io/bento4/bin/mp4hls"

DEBUG = _env_bool('DEBUG')

# CSRF 信任的 Origin — 必须与实际访问地址的 scheme+host+port 完全匹配
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8080',
    'http://localhost',
    'http://127.0.0.1:8080',
    'http://127.0.0.1',
]

# 如果 FRONTEND_HOST 不在上面列表里，动态追加
if FRONTEND_HOST not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(FRONTEND_HOST)

# 让 Nginx 正确转发 Host 头到 Django
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = _env_bool('SECURE_SSL_REDIRECT')
CSRF_COOKIE_SECURE = _env_bool('CSRF_COOKIE_SECURE', SECURE_SSL_REDIRECT)
SESSION_COOKIE_SECURE = _env_bool('SESSION_COOKIE_SECURE', SECURE_SSL_REDIRECT)

# 部署环境使用身份提供商选择页（账号密码 / 微信扫码）作为登录入口
# 测试环境保持关闭，测试用例断言的是 allauth 默认登录表单
USE_IDENTITY_PROVIDERS = _env_bool('USE_IDENTITY_PROVIDERS', not os.getenv('TESTING'))
