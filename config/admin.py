from django.contrib import admin

from config.models import ConfigEntry


@admin.register(ConfigEntry)
class ConfigEntryAdmin(admin.ModelAdmin):
    list_display = ('key', 'updated_at')
    search_fields = ('key',)
