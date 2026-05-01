from functools import wraps

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone

from .forms import (
    BikeForm,
    BookingRequestForm,
    CustomerDocumentForm,
    NotificationForm,
    ProfileForm,
    RegistrationForm,
)
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


class CustomerLoginView(LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        if self.request.user.is_staff:
            return reverse_lazy("staff_dashboard")
        return reverse_lazy("dashboard")


class CustomerLogoutView(LogoutView):
    next_page = reverse_lazy("login")


def home(request):
    if not request.user.is_authenticated:
        return redirect("login")
    if request.user.is_staff:
        return redirect("staff_dashboard")
    return redirect("dashboard")


def ensure_customer(user):
    if user.is_staff:
        raise PermissionDenied("Staff accounts use the admin dashboard.")
    customer, _ = Customer.objects.get_or_create(user=user)
    return customer


def customer_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapped(request, *args, **kwargs):
        if request.user.is_staff:
            messages.info(request, "Staff accounts use the admin dashboard.")
            return redirect("staff_dashboard")
        return view_func(request, *args, **kwargs)

    return wrapped


def register(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect("staff_dashboard")
        return redirect("dashboard")

    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Welcome! Your customer account is ready.")
        return redirect("dashboard")

    return render(request, "registration/register.html", {"form": form})


def staff_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("Only staff can access the admin dashboard.")
        return view_func(request, *args, **kwargs)

    return wrapped


@staff_required
def staff_dashboard(request):
    today = timezone.localdate()
    bookings = Booking.objects.select_related("customer__user", "bike")
    payments = Payment.objects.select_related("booking__customer__user", "booking__bike")
    verified_revenue = payments.filter(status=PaymentStatus.VERIFIED).aggregate(total=Sum("amount"))["total"] or 0

    context = {
        "active_staff_nav": "dashboard",
        "stats": {
            "today_bookings": bookings.filter(created_at__date=today).count(),
            "available_bikes": Bike.objects.filter(is_available=True).count(),
            "active_rentals": bookings.filter(status=BookingStatus.ACTIVE).count(),
            "pending_payments": payments.filter(
                status__in=[PaymentStatus.UNPAID, PaymentStatus.PENDING_VERIFICATION]
            ).count(),
            "returns_due": bookings.filter(
                status__in=[BookingStatus.CONFIRMED, BookingStatus.ACTIVE],
                return_datetime__date__lte=today,
            ).count(),
            "verified_revenue": verified_revenue,
        },
        "pending_bookings": bookings.filter(
            status__in=[BookingStatus.REQUESTED, BookingStatus.PENDING, BookingStatus.PAYMENT_PENDING]
        )[:5],
        "recent_payments": payments[:5],
        "pending_documents": CustomerDocument.objects.filter(
            status=CustomerDocument.VerificationStatus.PENDING
        ).select_related("customer__user")[:5],
    }
    return render(request, "rentals/staff/dashboard.html", context)


@staff_required
def staff_bikes(request):
    form = BikeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Bike added to the fleet.")
        return redirect("staff_bikes")

    bikes = Bike.objects.all()
    return render(
        request,
        "rentals/staff/bikes.html",
        {
            "active_staff_nav": "bikes",
            "form": form,
            "bikes": bikes,
        },
    )


@staff_required
def staff_bike_edit(request, pk):
    bike = get_object_or_404(Bike, pk=pk)
    form = BikeForm(request.POST or None, instance=bike)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Bike updated.")
        return redirect("staff_bikes")
    return render(
        request,
        "rentals/staff/bike_edit.html",
        {
            "active_staff_nav": "bikes",
            "form": form,
            "bike": bike,
        },
    )


@staff_required
def staff_bookings(request):
    if request.method == "POST":
        booking = get_object_or_404(Booking, pk=request.POST.get("booking_id"))
        new_status = request.POST.get("status")
        if new_status in BookingStatus.values:
            booking.status = new_status
            booking.save(update_fields=["status", "updated_at"])
            Payment.objects.get_or_create(
                booking=booking,
                defaults={"amount": booking.total_amount, "status": PaymentStatus.UNPAID},
            )
            messages.success(request, f"Booking #{booking.pk} updated to {booking.get_status_display()}.")
        return redirect("staff_bookings")

    status_filter = request.GET.get("status", "")
    bookings = Booking.objects.select_related("customer__user", "bike", "payment")
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    return render(
        request,
        "rentals/staff/bookings.html",
        {
            "active_staff_nav": "bookings",
            "bookings": bookings,
            "status_filter": status_filter,
            "booking_statuses": BookingStatus.choices,
        },
    )


@staff_required
def staff_payments(request):
    if request.method == "POST":
        payment = get_object_or_404(Payment, pk=request.POST.get("payment_id"))
        action = request.POST.get("action")
        if action == "verify":
            payment.status = PaymentStatus.VERIFIED
            payment.verified_by = request.user
            payment.verified_at = timezone.now()
            payment.save(update_fields=["status", "verified_by", "verified_at", "updated_at"])
            messages.success(request, "Cash payment verified and booking confirmed.")
        elif action == "reject":
            payment.status = PaymentStatus.REJECTED
            payment.save(update_fields=["status", "updated_at"])
            messages.warning(request, "Payment marked rejected.")
        return redirect("staff_payments")

    payments = Payment.objects.select_related("booking__customer__user", "booking__bike", "verified_by")
    return render(
        request,
        "rentals/staff/payments.html",
        {
            "active_staff_nav": "payments",
            "payments": payments,
        },
    )


@staff_required
def staff_customers(request):
    customers = Customer.objects.select_related("user").annotate(total_bookings=Count("bookings"))
    return render(
        request,
        "rentals/staff/customers.html",
        {
            "active_staff_nav": "customers",
            "customers": customers,
        },
    )


@staff_required
def staff_documents(request):
    if request.method == "POST":
        document = get_object_or_404(CustomerDocument, pk=request.POST.get("document_id"))
        action = request.POST.get("action")
        if action == "verify":
            document.status = CustomerDocument.VerificationStatus.VERIFIED
            document.verified_at = timezone.now()
            document.save(update_fields=["status", "verified_at"])
            messages.success(request, "Document verified.")
        elif action == "reject":
            document.status = CustomerDocument.VerificationStatus.REJECTED
            document.save(update_fields=["status"])
            messages.warning(request, "Document rejected.")
        return redirect("staff_documents")

    documents = CustomerDocument.objects.select_related("customer__user")
    return render(
        request,
        "rentals/staff/documents.html",
        {
            "active_staff_nav": "documents",
            "documents": documents,
        },
    )


@staff_required
def staff_notifications(request):
    form = NotificationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Notification sent to customer.")
        return redirect("staff_notifications")

    notifications = Notification.objects.select_related("customer__user")
    return render(
        request,
        "rentals/staff/notifications.html",
        {
            "active_staff_nav": "notifications",
            "form": form,
            "notifications": notifications[:20],
        },
    )


@staff_required
def staff_reports(request):
    today = timezone.localdate()
    month_start = today.replace(day=1)
    bookings = Booking.objects.select_related("bike", "customer__user")
    payments = Payment.objects.select_related("booking")
    status_counts = bookings.values("status").annotate(total=Count("id")).order_by("status")
    bike_usage = Bike.objects.annotate(total_bookings=Count("bookings")).order_by("-total_bookings")[:8]
    context = {
        "active_staff_nav": "reports",
        "report_stats": {
            "daily_bookings": bookings.filter(created_at__date=today).count(),
            "monthly_bookings": bookings.filter(created_at__date__gte=month_start).count(),
            "monthly_revenue": payments.filter(
                status=PaymentStatus.VERIFIED,
                verified_at__date__gte=month_start,
            ).aggregate(total=Sum("amount"))["total"] or 0,
            "cancelled_bookings": bookings.filter(status=BookingStatus.CANCELLED).count(),
        },
        "status_counts": status_counts,
        "bike_usage": bike_usage,
    }
    return render(request, "rentals/staff/reports.html", context)


@customer_required
def dashboard(request):
    customer = ensure_customer(request.user)
    bookings = Booking.objects.filter(customer=customer).select_related("bike")
    counts = bookings.aggregate(
        total=Count("id"),
        approved=Count("id", filter=Q(status=BookingStatus.APPROVED)),
        pending=Count(
            "id",
            filter=Q(
                status__in=[
                    BookingStatus.REQUESTED,
                    BookingStatus.PENDING,
                    BookingStatus.PAYMENT_PENDING,
                ]
            ),
        ),
        cancelled=Count("id", filter=Q(status=BookingStatus.CANCELLED)),
    )
    context = {
        "active_nav": "dashboard",
        "summary": counts,
        "recent_bookings": bookings[:4],
        "latest_notifications": Notification.objects.filter(customer=customer)[:5],
    }
    return render(request, "rentals/dashboard.html", context)


@customer_required
def browse_bikes(request):
    customer = ensure_customer(request.user)
    form = BookingRequestForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        bike = get_object_or_404(Bike, pk=form.cleaned_data["bike_id"], is_available=True)
        booking = Booking.objects.create(
            customer=customer,
            bike=bike,
            pickup_datetime=form.cleaned_data["pickup_datetime"],
            return_datetime=form.cleaned_data["return_datetime"],
            notes=form.cleaned_data.get("notes", ""),
            status=BookingStatus.REQUESTED,
        )
        Payment.objects.create(
            booking=booking,
            amount=booking.total_amount,
            status=PaymentStatus.UNPAID,
        )
        messages.success(request, "Booking request submitted. The office team will review it soon.")
        return redirect("my_bookings")

    bikes = Bike.objects.filter(is_available=True)
    return render(
        request,
        "rentals/browse_bikes.html",
        {
            "active_nav": "browse_bikes",
            "bikes": bikes,
            "form": form,
        },
    )


@customer_required
def my_bookings(request):
    customer = ensure_customer(request.user)
    bookings = Booking.objects.filter(customer=customer).select_related("bike", "payment")
    return render(
        request,
        "rentals/my_bookings.html",
        {
            "active_nav": "my_bookings",
            "bookings": bookings,
        },
    )


@customer_required
def booking_detail(request, pk):
    customer = ensure_customer(request.user)
    booking = get_object_or_404(
        Booking.objects.select_related("bike", "payment"),
        pk=pk,
        customer=customer,
    )

    if request.method == "POST" and request.POST.get("action") == "cancel" and booking.can_cancel:
        booking.status = BookingStatus.CANCELLED
        booking.save(update_fields=["status", "updated_at"])
        messages.info(request, "Your booking was cancelled.")
        return redirect("my_bookings")

    return render(
        request,
        "rentals/booking_detail.html",
        {
            "active_nav": "my_bookings",
            "booking": booking,
        },
    )


@customer_required
def payments(request):
    customer = ensure_customer(request.user)
    payment_list = Payment.objects.filter(booking__customer=customer).select_related("booking__bike")
    return render(
        request,
        "rentals/payments.html",
        {
            "active_nav": "payments",
            "payments": payment_list,
        },
    )


@customer_required
def documents(request):
    customer = ensure_customer(request.user)
    form = CustomerDocumentForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        document = form.save(commit=False)
        document.customer = customer
        document.save()
        messages.success(request, "Document uploaded for office verification.")
        return redirect("documents")

    return render(
        request,
        "rentals/documents.html",
        {
            "active_nav": "documents",
            "form": form,
            "documents": CustomerDocument.objects.filter(customer=customer),
        },
    )


@customer_required
def profile(request):
    customer = ensure_customer(request.user)
    form = ProfileForm(request.POST or None, instance=customer)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("profile")

    return render(
        request,
        "rentals/profile.html",
        {
            "active_nav": "profile",
            "form": form,
        },
    )


@customer_required
def notifications(request):
    customer = ensure_customer(request.user)

    if request.method == "POST":
        notification_id = request.POST.get("notification_id")
        if request.POST.get("action") == "mark_all_read":
            Notification.objects.filter(customer=customer, is_read=False).update(is_read=True)
            messages.success(request, "All notifications marked as read.")
        elif notification_id:
            Notification.objects.filter(customer=customer, pk=notification_id).update(is_read=True)
        return redirect("notifications")

    return render(
        request,
        "rentals/notifications.html",
        {
            "active_nav": "notifications",
            "notifications": Notification.objects.filter(customer=customer),
        },
    )
