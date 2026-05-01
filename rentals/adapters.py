from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from .models import Customer


class CustomerSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        Customer.objects.get_or_create(
            user=user,
            defaults={
                "phone": "",
                "address": "",
                "license_number": "",
            },
        )
        return user
