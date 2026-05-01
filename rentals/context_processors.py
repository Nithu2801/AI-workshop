from .models import Customer, Notification


def notification_panel(request):
    if not request.user.is_authenticated:
        return {
            "panel_notifications": [],
            "unread_notifications_count": 0,
        }

    customer = Customer.objects.filter(user=request.user).first()
    if not customer:
        return {
            "panel_notifications": [],
            "unread_notifications_count": 0,
        }

    notifications = Notification.objects.filter(customer=customer)
    return {
        "panel_notifications": notifications[:6],
        "unread_notifications_count": notifications.filter(is_read=False).count(),
    }


def google_oauth(request):
    try:
        from allauth.socialaccount.models import SocialApp

        google_ready = SocialApp.objects.filter(provider="google", sites__id=1).exists()
    except Exception:
        google_ready = False

    return {
        "google_oauth_ready": google_ready,
    }
