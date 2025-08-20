from django.apps import AppConfig
# import cloudinary  # ← Commented out import

class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        import core.signals # Keep signals!

        # TODO: Remove after full migration to local storage
        # import cloudinary
        # cloudinary.config(
        #     cloud_name="detylqmth",
        #     api_key="595366268117915",
        #     api_secret="CfNRF44_mEntTNTt2ZFaJa1k2tY",
        #     secure=True,
        # )