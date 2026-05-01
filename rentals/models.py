from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class Customer(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    license_number = models.CharField(max_length=60, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["user__first_name", "user__username"]

    def __str__(self):
        return self.full_name or self.user.username

    @property
    def full_name(self):
        name = self.user.get_full_name().strip()
        return name or self.user.username


class Bike(models.Model):
    name = models.CharField(max_length=120)
    model = models.CharField(max_length=120)
    number_plate = models.CharField(max_length=30, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="bikes/", blank=True)
    image_url = models.URLField(blank=True)
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2)
    engine_cc = models.PositiveIntegerField(default=125)
    fuel_type = models.CharField(max_length=40, default="Petrol")
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "model"]

    def __str__(self):
        return f"{self.name} {self.model} ({self.number_plate})"

    @property
    def image_src(self):
        if self.image:
            return self.image.url
        return self.image_url or "https://placehold.co/900x600/e5e7eb/111827?text=Motorbike"


class BookingStatus(models.TextChoices):
    REQUESTED = "REQUESTED", "Requested"
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    PAYMENT_PENDING = "PAYMENT_PENDING", "Payment Pending"
    CONFIRMED = "CONFIRMED", "Confirmed"
    ACTIVE = "ACTIVE", "Active Rental"
    COMPLETED = "COMPLETED", "Completed"
    REJECTED = "REJECTED", "Rejected"
    CANCELLED = "CANCELLED", "Cancelled"


class Booking(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="bookings")
    bike = models.ForeignKey(Bike, on_delete=models.PROTECT, related_name="bookings")
    pickup_datetime = models.DateTimeField()
    return_datetime = models.DateTimeField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(
        max_length=30,
        choices=BookingStatus.choices,
        default=BookingStatus.REQUESTED,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer} - {self.bike} - {self.get_status_display()}"

    @property
    def rental_days(self):
        if not self.pickup_datetime or not self.return_datetime:
            return 1
        seconds = max(0, int((self.return_datetime - self.pickup_datetime).total_seconds()))
        return max(1, (seconds + 86399) // 86400)

    @property
    def status_badge_class(self):
        return {
            BookingStatus.REQUESTED: "badge-soft-warning",
            BookingStatus.PENDING: "badge-soft-warning",
            BookingStatus.PAYMENT_PENDING: "badge-soft-warning",
            BookingStatus.APPROVED: "badge-soft-success",
            BookingStatus.CONFIRMED: "badge-soft-success",
            BookingStatus.ACTIVE: "badge-soft-primary",
            BookingStatus.COMPLETED: "badge-soft-primary",
            BookingStatus.REJECTED: "badge-soft-danger",
            BookingStatus.CANCELLED: "badge-soft-danger",
        }.get(self.status, "badge-soft-secondary")

    @property
    def can_cancel(self):
        return self.status in {
            BookingStatus.REQUESTED,
            BookingStatus.PENDING,
            BookingStatus.APPROVED,
            BookingStatus.PAYMENT_PENDING,
        }

    def save(self, *args, **kwargs):
        old_status = None
        if self.pk:
            old_status = Booking.objects.filter(pk=self.pk).values_list("status", flat=True).first()

        if self.bike_id and self.pickup_datetime and self.return_datetime:
            self.total_amount = self.bike.daily_rate * Decimal(self.rental_days)

        super().save(*args, **kwargs)

        if old_status is None or old_status != self.status:
            titles = {
                BookingStatus.REQUESTED: "Booking Requested",
                BookingStatus.PENDING: "Booking Pending",
                BookingStatus.APPROVED: "Booking Approved",
                BookingStatus.PAYMENT_PENDING: "Payment Reminder",
                BookingStatus.CONFIRMED: "Booking Confirmed",
                BookingStatus.ACTIVE: "Rental Started",
                BookingStatus.COMPLETED: "Rental Completed",
                BookingStatus.REJECTED: "Booking Rejected",
                BookingStatus.CANCELLED: "Booking Cancelled",
            }
            messages = {
                BookingStatus.REQUESTED: "Your rental request has been received.",
                BookingStatus.PENDING: "Your booking is pending admin review.",
                BookingStatus.APPROVED: "Your booking has been approved. Please visit the office to pay cash.",
                BookingStatus.PAYMENT_PENDING: "Please visit the office to complete your cash payment.",
                BookingStatus.CONFIRMED: "Your booking is confirmed after manual payment verification.",
                BookingStatus.ACTIVE: "Your active rental period has started.",
                BookingStatus.COMPLETED: "Your rental has been completed. Thank you for riding with us.",
                BookingStatus.REJECTED: "Your booking request was rejected by the office.",
                BookingStatus.CANCELLED: "Your booking has been cancelled.",
            }
            self.create_status_notification(titles.get(self.status, "Booking Updated"), messages.get(self.status, "Your booking status was updated."))

    def create_status_notification(self, title, message):
        Notification.objects.create(
            customer=self.customer,
            title=title,
            message=f"{message} Bike: {self.bike.name} {self.bike.model}.",
            notification_type=Notification.NotificationType.BOOKING,
        )


class PaymentStatus(models.TextChoices):
    UNPAID = "UNPAID", "Unpaid"
    PENDING_VERIFICATION = "PENDING_VERIFICATION", "Pending Verification"
    VERIFIED = "VERIFIED", "Verified"
    REJECTED = "REJECTED", "Rejected"


class Payment(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="payment")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=30,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
    )
    method = models.CharField(max_length=40, default="Cash at Office")
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verified_payments",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.booking} - {self.get_status_display()}"

    @property
    def status_badge_class(self):
        return {
            PaymentStatus.UNPAID: "badge-soft-warning",
            PaymentStatus.PENDING_VERIFICATION: "badge-soft-warning",
            PaymentStatus.VERIFIED: "badge-soft-success",
            PaymentStatus.REJECTED: "badge-soft-danger",
        }.get(self.status, "badge-soft-secondary")

    def save(self, *args, **kwargs):
        old_status = None
        if self.pk:
            old_status = Payment.objects.filter(pk=self.pk).values_list("status", flat=True).first()

        if self.status == PaymentStatus.VERIFIED and not self.verified_at:
            self.verified_at = timezone.now()

        super().save(*args, **kwargs)

        if old_status != self.status and self.status == PaymentStatus.VERIFIED:
            Notification.objects.create(
                customer=self.booking.customer,
                title="Payment Verified",
                message="Your cash payment has been verified by the office.",
                notification_type=Notification.NotificationType.PAYMENT,
            )
            if self.booking.status in {
                BookingStatus.APPROVED,
                BookingStatus.PAYMENT_PENDING,
                BookingStatus.PENDING,
            }:
                self.booking.status = BookingStatus.CONFIRMED
                self.booking.save(update_fields=["status", "updated_at"])


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        BOOKING = "BOOKING", "Booking"
        PAYMENT = "PAYMENT", "Payment"
        REMINDER = "REMINDER", "Reminder"
        SYSTEM = "SYSTEM", "System"

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=120)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM,
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - {self.customer}"


class CustomerDocument(models.Model):
    class DocumentType(models.TextChoices):
        ID_CARD = "ID_CARD", "ID Card / Passport"
        LICENSE = "LICENSE", "Driving License"
        OTHER = "OTHER", "Other"

    class VerificationStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        VERIFIED = "VERIFIED", "Verified"
        REJECTED = "REJECTED", "Rejected"

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    file = models.FileField(upload_to="documents/")
    status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )
    notes = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.customer} - {self.get_document_type_display()}"

    @property
    def status_badge_class(self):
        return {
            self.VerificationStatus.PENDING: "badge-soft-warning",
            self.VerificationStatus.VERIFIED: "badge-soft-success",
            self.VerificationStatus.REJECTED: "badge-soft-danger",
        }.get(self.status, "badge-soft-secondary")

    def save(self, *args, **kwargs):
        old_status = None
        if self.pk:
            old_status = CustomerDocument.objects.filter(pk=self.pk).values_list("status", flat=True).first()

        if self.status == self.VerificationStatus.VERIFIED and not self.verified_at:
            self.verified_at = timezone.now()

        super().save(*args, **kwargs)

        if old_status and old_status != self.status:
            Notification.objects.create(
                customer=self.customer,
                title=f"Document {self.get_status_display()}",
                message=f"Your {self.get_document_type_display()} document status is now {self.get_status_display().lower()}.",
                notification_type=Notification.NotificationType.SYSTEM,
            )
