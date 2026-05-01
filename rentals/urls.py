from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("admin/", views.staff_dashboard, name="staff_dashboard"),
    path("admin/bikes/", views.staff_bikes, name="staff_bikes"),
    path("admin/bikes/<int:pk>/edit/", views.staff_bike_edit, name="staff_bike_edit"),
    path("admin/bookings/", views.staff_bookings, name="staff_bookings"),
    path("admin/payments/", views.staff_payments, name="staff_payments"),
    path("admin/customers/", views.staff_customers, name="staff_customers"),
    path("admin/documents/", views.staff_documents, name="staff_documents"),
    path("admin/notifications/", views.staff_notifications, name="staff_notifications"),
    path("admin/reports/", views.staff_reports, name="staff_reports"),
    path("customer/", views.dashboard, name="dashboard"),
    path("login/", views.CustomerLoginView.as_view(), name="login"),
    path("logout/", views.CustomerLogoutView.as_view(), name="logout"),
    path("register/", views.register, name="register"),
    path("browse-bikes/", views.browse_bikes, name="browse_bikes"),
    path("bookings/", views.my_bookings, name="my_bookings"),
    path("bookings/<int:pk>/", views.booking_detail, name="booking_detail"),
    path("payments/", views.payments, name="payments"),
    path("documents/", views.documents, name="documents"),
    path("profile/", views.profile, name="profile"),
    path("notifications/", views.notifications, name="notifications"),
]
