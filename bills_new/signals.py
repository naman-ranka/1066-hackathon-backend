from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Person

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a Person profile when a new User is created"""
    if created:
        Person.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the Person profile when the User is updated"""
    try:
        instance.profile.save()
    except Person.DoesNotExist:
        # Create the profile if it doesn't exist
        Person.objects.create(user=instance)