# In attachments/signals.py
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Attachment

@receiver(pre_save, sender=Attachment)
def update_attachment_status(sender, instance, **kwargs):
    if instance.status == 'active' and timezone.now().date() > instance.end_date:
        instance.status = 'completed'
        instance.completed_date = timezone.now()