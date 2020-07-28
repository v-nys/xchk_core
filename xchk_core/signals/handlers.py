from django.conf import settings
from django.utils.translation import ugettext_noop as _
from django.db.models.signals import pre_save, post_migrate, post_save
from django.dispatch import receiver
from ..models import FeedbackTicket, FeedbackType
from pinax.notifications.models import send_now
from django.core.exceptions import ObjectDoesNotExist


@receiver(post_migrate)
def create_notice_types(sender, **kwargs): 
    if "pinax.notifications" in settings.INSTALLED_APPS:
        from pinax.notifications.models import NoticeType
        print("Creating notices for checkerapp")
        NoticeType.create("assignment_feedback", _("Feedback op opdracht ontvangen"), _("Je hebt feedback ontvangen op een opdracht die je hebt ingezonden."))
        NoticeType.create("new_feedback_ticket", _("Received new feedback ticket"), _("You have received a new feedback ticket."))
    else:
        print("Skipping creation of NoticeTypes as notification app not found")

@receiver(post_save)
def notify_feedback_ticket(sender, instance, raw, using, update_fields, **kwargs):
    if sender == FeedbackTicket:
        from dbchecker.users.models import User
        owner = User.objects.get(pk = 1)
        send_now([owner],"new_feedback_ticket",{"feedback_ticket": instance, "message": instance.message})
