import warnings

import django.db.utils
from django.db import models


class ConfigEntry(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def get(cls, key: str, default=None):
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            return default
        except django.db.utils.OperationalError:
            warnings.warn('Database is not ready yet. Please run migrations.')
            return default

    @classmethod
    def set(cls, key: str, value: str):
        obj, _ = cls.objects.update_or_create(
            key=key,
            defaults={'value': value},
        )
        return obj

    @classmethod
    def remove(cls, key: str):
        try:
            cls.objects.get(key=key).delete()
        except cls.DoesNotExist:
            return None

    def __str__(self):
        return self.key
