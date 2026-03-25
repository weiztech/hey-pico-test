from django.db import models


class AccessPermission(models.TextChoices):
    GOOGLE_MAP_API = "Google Map API", "Google Map API"
    MY_API = "My API", "My API"
    OTHER_3RD_PARTY_API = "Other 3rd party API", "Other 3rd party API"
