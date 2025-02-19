from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    pass

class UserPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preference')
    dark_mode = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}'s preferences"