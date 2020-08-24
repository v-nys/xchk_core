from django.conf import settings
from django.utils.translation import ugettext_noop as _
from django.db.models.signals import pre_save, post_migrate, post_save
from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from ..models import FeedbackTicket, FeedbackType
from pinax.notifications.models import send_now
from django.core.exceptions import ObjectDoesNotExist
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend as crypto_default_backend
import requests

@receiver(user_signed_up)
def create_gitea_account(request, user, **kwargs):
    print(dir(user))
    url = f'http://gitea:3000/api/v1/admin/users'
    data = {'email' : user.email,
            'login_name' : user.username,
            'must_change_password' : True,
            'password' : user.initial_pw}
    headers = {'accept': 'application/json', 'Content-Type': 'application/json', 'Authorization': f'token {settings.GITEA_APPLICATION_TOKEN}'}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    key = rsa.generate_private_key(
        backend=crypto_default_backend(),
        public_exponent=65537,
        key_size=2048
    )
    private_key = key.private_bytes(
        crypto_serialization.Encoding.PEM,
        crypto_serialization.PrivateFormat.PKCS8,
        crypto_serialization.NoEncryption())
    public_key = key.public_key().public_bytes(
        crypto_serialization.Encoding.OpenSSH,
        crypto_serialization.PublicFormat.OpenSSH
    )
    print(private_key)
    url = f'http://gitea:3000/api/v1/admin/users/{user.username}/keys'
    data = {'key' : str(public_key), 'read_only': False, 'title': 'key generated by xchk'}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    user.initial_private_key = str(private_key)
    user.save()

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
