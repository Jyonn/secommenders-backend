from config.models import ConfigEntry


class Space:
    @property
    def auth(self):
        return ConfigEntry.get('auth', default=None)


Space = Space()
