from types import MethodType

from django.contrib import admin, messages
from django.db.models import Sum
from django.utils import timezone

from .models import (
    Bike,
    Booking,
    BookingStatus,
    Customer,
    CustomerDocument,
    Notification,
    Payment,
    PaymentStatus,
)

admin.site.site_header = "Motorbike Rental Admin"
admin.site.site_title = "Rental Admin"
admin.site.index_title = "Office Dashboard"
admin.site.index_template = "admin/index.html"


_original_admin_index = admin.site.index


def rental_admin_index(self, request, extra_context=None):
    today = timezone.localdate()
    extra_context = extra_context or {}
    verified_revenue = Payment.objects.filter(status=PaymentStatus.VERIFIED).aggregate(
        total=Sum("amount")
    )["total"] or 0
    extra_context["dashboard_stats"] = {
        "today_bookings": Booking.objects.filter(created_at__date=today).count(),
        "available_bikes": Bike.objects.filter(is_available=True).count(),
        "active_rentals": Booking.objects.filter(status=BookingStatus.ACTIVE).count(),
        "pending_payments": Payment.objects.filter(
            status__in=[PaymentStatus.UNPAID, PaymentStatus.PENDING_VERIFICATION]
        ).count(),
        "returns_due": Booking.objects.filter(
            status__in=[BookingStatus.CONFIRMED, BookingStatus.ACTIVE],
            return_datetime__date__lte=today,
        ).count(),
        "verified_revenue": verified_revenue,
    }
    return _original_admin_index(request, extra_context=extra_context)


admin.site.index = MethodType(rental_admin_index, admin.site)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone", "license_number", "created_at")
    search_fields = ("user__username", "user__first_name", "user__last_name", "phone", "license_number")
    list_select_related = ("user",)


@admin.register(Bike)
class BikeAdmin(admin.ModelAdmin):
    list_display = ("name", "model", "number_plate", "daily_rate", "engine_cc", "is_available")
    list_filter = ("is_available", "fuel_type")
    search_fields = ("name", "model", "number_plate")


class PaymentInline(admin.StackedInline):
    model = Payment
    extra = 0
    can_delete = False


@admin.action(description="Mark selected bookings as approved")
def approve_bookings(modeladmin, request, queryset):
    for booking in queryset:
        booking.status = BookingStatus.APPROVED
        booking.save(update_fields=["status", "updated_at"])
    messages.success(request, f"{queryset.count()} booking(s) marked approved.")


@admin.action(description="Mark selected bookings as payment pending")
def mark_payment_pending(modeladmin, request, queryset):
    for booking in queryset:
        booking.status = BookingStatus.PAYMENT_PENDING
        booking.save(update_fields=["status", "updated_at"])
    messages.success(request, f"{queryset.count()} booking(s) marked payment pending.")


@admin.action(description="Reject selected bookings")
def reject_bookings(modeladmin, request, queryset):
    for booking in queryset:
        booking.status = BookingStatus.REJECTED
        booking.save(update_fields=["status", "updated_at"])
    messages.warning(request, f"{queryset.count()} booking(s) rejected.")


@admin.action(description="Mark selected bookings as active rentals")
def activate_rentals(modeladmin, request, queryset):
    for booking in queryset:
        booking.status = BookingStatus.ACTIVE
        booking.save(update_fields=["status", "updated_at"])
    messages.success(request, f"{queryset.count()} booking(s) marked active.")


@admin.action(description="Mark selected bookings as completed")
def complete_bookings(modeladmin, request, queryset):
    for booking in queryset:
        booking.status = BookingStatus.COMPLETED
        booking.save(update_fields=["status", "updated_at"])
    messages.success(request, f"{queryset.count()} booking(s) completed.")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "bike",
        "pickup_datetime",
        "return_datetime",
        "total_amount",
        "status",
        "created_at",
    )
    list_filter = ("status", "pickup_datetime", "created_at")
    search_fields = ("customer__user__username", "customer__user__first_name", "customer__user__last_name", "bike__name", "bike__number_plate")
    list_select_related = ("customer__user", "bike")
    inlines = [PaymentInline]
    actions = [approve_bookings, mark_payment_pending, reject_bookings, activate_rentals, complete_bookings]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        payment, created = Payment.objects.get_or_create(
            booking=obj,
            defaults={"amount": obj.total_amount, "status": PaymentStatus.UNPAID},
        )
        if not created and payment.amount != obj.total_amount:
            payment.amount = obj.total_amount
            payment.save(update_fields=["amount", "updated_at"])


@admin.action(description="Confirm selected cash payments")
def confirm_cash_payments(modeladmin, request, queryset):
    count = 0
    for payment in queryset:
        payment.status = PaymentStatus.VERIFIED
        payment.verified_by = request.user
        payment.verified_at = timezone.now()
        payment.save(update_fields=["status", "verified_by", "verified_at", "updated_at"])
        count += 1
    messages.success(request, f"{count} cash payment(s) verified.")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("booking", "amount", "method", "status", "verified_by", "verified_at", "created_at")
    list_filter = ("status", "method", "created_at")
    search_fields = ("booking__customer__user__username", "booking__bike__name", "booking__bike__number_plate")
    list_select_related = ("booking__customer__user", "booking__bike", "verified_by")
    actions = [confirm_cash_payments]

    def save_model(self, request, obj, form, change):
        if obj.status == PaymentStatus.VERIFIED and not obj.verified_by:
            obj.verified_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "customer", "notification_type", "is_read", "created_at")
    list_filter = ("notification_type", "is_read", "created_at")
    search_fields = ("title", "message", "customer__user__username")
    list_select_related = ("customer__user",)


@admin.action(description="Mark selected documents as verified")
def verify_documents(modeladmin, request, queryset):
    count = 0
    for document in queryset:
        document.status = CustomerDocument.VerificationStatus.VERIFIED
        document.verified_at = timezone.now()
        document.save(update_fields=["status", "verified_at"])
        count += 1
    messages.success(request, f"{count} document(s) verified.")


@admin.register(CustomerDocument)
class CustomerDocumentAdmin(admin.ModelAdmin):
    list_display = ("customer", "document_type", "status", "uploaded_at", "verified_at")
    list_filter = ("document_type", "status", "uploaded_at")
    search_fields = ("customer__user__username", "customer__user__first_name", "customer__user__last_name")
    list_select_related = ("customer__user",)
    actions = [verify_documents]
