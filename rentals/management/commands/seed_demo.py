from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from django.utils import timezone

from rentals.models import (
    Bike,
    Booking,
    BookingStatus,
    Customer,
    CustomerDocument,
    Notification,
    Payment,
    PaymentStatus,
)


class Command(BaseCommand):
    help = "Create demo users, bikes, bookings, payments, documents, and notifications."

    def handle(self, *args, **options):
        Site.objects.update_or_create(
            id=1,
            defaults={"domain": "127.0.0.1:8000", "name": "Motorbike Rental Local"},
        )
        admin = self.create_user(
            username="admin",
            password="Admin@12345",
            email="admin@example.com",
            first_name="Office",
            last_name="Admin",
            is_staff=True,
            is_superuser=True,
        )
        customer_user = self.create_user(
            username="customer",
            password="Customer@12345",
            email="customer@example.com",
            first_name="Demo",
            last_name="Customer",
        )
        customer, _ = Customer.objects.update_or_create(
            user=customer_user,
            defaults={
                "phone": "+94 77 123 4567",
                "address": "42 Galle Road, Colombo",
                "license_number": "B1234567",
            },
        )

        bikes = self.create_bikes()
        Booking.objects.filter(customer=customer).delete()
        Notification.objects.filter(customer=customer).delete()
        CustomerDocument.objects.filter(customer=customer).delete()

        now = timezone.now().replace(minute=0, second=0, microsecond=0)
        booking_specs = [
            (bikes[0], BookingStatus.REQUESTED, now + timedelta(days=1), now + timedelta(days=3), PaymentStatus.UNPAID),
            (bikes[1], BookingStatus.PENDING, now + timedelta(days=4), now + timedelta(days=6), PaymentStatus.UNPAID),
            (bikes[2], BookingStatus.APPROVED, now + timedelta(days=7), now + timedelta(days=10), PaymentStatus.PENDING_VERIFICATION),
            (bikes[3], BookingStatus.ACTIVE, now - timedelta(days=1), now + timedelta(days=1), PaymentStatus.VERIFIED),
            (bikes[4], BookingStatus.COMPLETED, now - timedelta(days=9), now - timedelta(days=6), PaymentStatus.VERIFIED),
            (bikes[0], BookingStatus.CANCELLED, now + timedelta(days=12), now + timedelta(days=14), PaymentStatus.REJECTED),
        ]

        for bike, status, pickup, return_at, payment_status in booking_specs:
            booking = Booking.objects.create(
                customer=customer,
                bike=bike,
                pickup_datetime=pickup,
                return_datetime=return_at,
                status=status,
                notes="Seed demo booking",
            )
            Payment.objects.create(
                booking=booking,
                amount=booking.total_amount,
                status=payment_status,
                verified_by=admin if payment_status == PaymentStatus.VERIFIED else None,
                verified_at=timezone.now() if payment_status == PaymentStatus.VERIFIED else None,
            )

        Notification.objects.filter(customer=customer).delete()
        self.create_notifications(customer)
        self.create_document(customer)

        self.stdout.write(self.style.SUCCESS("Demo data created successfully."))
        self.stdout.write("Admin login:    admin / Admin@12345")
        self.stdout.write("Customer login: customer / Customer@12345")

    def create_user(self, username, password, email, first_name, last_name, is_staff=False, is_superuser=False):
        user, _ = User.objects.get_or_create(username=username)
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        user.set_password(password)
        user.save()
        return user

    def create_bikes(self):
        bike_data = [
            {
                "name": "Yamaha",
                "model": "MT-15",
                "number_plate": "WP-MB-1001",
                "daily_rate": Decimal("3500.00"),
                "engine_cc": 155,
                "fuel_type": "Petrol",
                "image_url": "https://images.unsplash.com/photo-1558981403-c5f9899a28bc?auto=format&fit=crop&w=900&q=80",
                "description": "Lightweight street bike with sporty handling for city rides.",
            },
            {
                "name": "Honda",
                "model": "PCX 160",
                "number_plate": "WP-MB-1002",
                "daily_rate": Decimal("4200.00"),
                "engine_cc": 160,
                "fuel_type": "Petrol",
                "image_url": "https://images.unsplash.com/photo-1591637333184-19aa84b3e01f?auto=format&fit=crop&w=900&q=80",
                "description": "Comfortable scooter with storage space and smooth automatic riding.",
            },
            {
                "name": "Royal Enfield",
                "model": "Classic 350",
                "number_plate": "WP-MB-1003",
                "daily_rate": Decimal("5500.00"),
                "engine_cc": 349,
                "fuel_type": "Petrol",
                "image_url": "https://images.unsplash.com/photo-1619771914272-e3c1ba17ba4d?auto=format&fit=crop&w=900&q=80",
                "description": "Classic cruiser feel for relaxed longer trips.",
            },
            {
                "name": "TVS",
                "model": "Ntorq 125",
                "number_plate": "WP-MB-1004",
                "daily_rate": Decimal("2800.00"),
                "engine_cc": 125,
                "fuel_type": "Petrol",
                "image_url": "https://images.unsplash.com/photo-1609630875171-b1321377ee65?auto=format&fit=crop&w=900&q=80",
                "description": "Agile scooter for short errands and daily commutes.",
            },
            {
                "name": "Bajaj",
                "model": "Pulsar NS200",
                "number_plate": "WP-MB-1005",
                "daily_rate": Decimal("3900.00"),
                "engine_cc": 199,
                "fuel_type": "Petrol",
                "image_url": "https://images.unsplash.com/photo-1611241443322-78d347f1ce07?auto=format&fit=crop&w=900&q=80",
                "description": "Sporty naked bike with strong performance for experienced riders.",
            },
        ]

        bikes = []
        for data in bike_data:
            bike, _ = Bike.objects.update_or_create(
                number_plate=data["number_plate"],
                defaults={**data, "is_available": True},
            )
            bikes.append(bike)
        return bikes

    def create_notifications(self, customer):
        notifications = [
            (
                "Booking Approved",
                "Your Yamaha MT-15 booking has been approved. Please visit the office to pay cash.",
                Notification.NotificationType.BOOKING,
                False,
            ),
            (
                "Booking Pending",
                "Your Honda PCX 160 request is waiting for office review.",
                Notification.NotificationType.BOOKING,
                False,
            ),
            (
                "Payment Reminder",
                "Cash payment must be completed at the office before pickup.",
                Notification.NotificationType.PAYMENT,
                False,
            ),
            (
                "Return Reminder",
                "Your active rental is due for return soon. Please check the return time.",
                Notification.NotificationType.REMINDER,
                True,
            ),
        ]
        for title, message, notification_type, is_read in notifications:
            Notification.objects.create(
                customer=customer,
                title=title,
                message=message,
                notification_type=notification_type,
                is_read=is_read,
            )

    def create_document(self, customer):
        document = CustomerDocument(
            customer=customer,
            document_type=CustomerDocument.DocumentType.LICENSE,
            status=CustomerDocument.VerificationStatus.PENDING,
            notes="Demo license document awaiting verification.",
        )
        document.file.save(
            "demo-license.txt",
            ContentFile("Demo driving license placeholder for Motorbike Rental System."),
            save=True,
        )
