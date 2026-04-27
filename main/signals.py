from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Users, Abiturient

# Создает запись в таблице Users при регистрации нового пользователя
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Users.objects.get_or_create(
            user_id=instance.id,
            defaults={
                'role': 'student',
                'password': instance.password,
                'login': instance.username,
                'is_activ': True,
            }
        )