"""Helpers for tests that run the app as several signed-in users behind a trusted proxy."""
PROXY_IP = "10.0.0.5"
ADMIN = {"x-authentik-uid": "u-henrik", "x-authentik-username": "henrik", "x-authentik-name": "Henrik", "x-authentik-groups": "homelab-admins|homelab-family"}
FAMILY = {"x-authentik-uid": "u-anna", "x-authentik-username": "anna", "x-authentik-name": "Anna", "x-authentik-groups": "homelab-family"}
OUTSIDER = {"x-authentik-uid": "u-x", "x-authentik-username": "x", "x-authentik-groups": "something-else"}


class FromAddress:
    """Makes every request look like it comes from `host` (TestClient always says 'testclient')."""

    def __init__(self, app, host):
        self.app, self.host = app, host

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            scope = {**scope, "client": (self.host, 50000)}
        await self.app(scope, receive, send)


def patch_settings(monkeypatch, **values):
    import app.services.family_service as family_service
    import app.services.strava_service as strava_service
    import app.services.user_service as user_service
    import app.strava as strava_module

    for module in (user_service, strava_service, strava_module, family_service):
        for key, value in values.items():
            monkeypatch.setattr(module.settings, key, value)
