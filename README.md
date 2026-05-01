# Motorbike Rental System

A runnable Django motorbike rental system with separate customer and office/admin dashboards using Python, Django, SQLite, Bootstrap 5, and Django templates.

## Features

- Customer dashboard with sidebar navigation, summary cards, booking cards, payments, documents, profile, and notifications.
- Custom office/admin dashboard for bikes, bookings, payments, customers, documents, notifications, and reports.
- Bike management with uploaded bike images, pricing, number plates, and availability.
- Browse Bikes page where customers request rentals with pickup and return date/time.
- Offline payment workflow: customers pay cash at the office, and staff verify payments manually in the admin dashboard.
- Raw Django admin remains available at `/django-admin/` for advanced database editing.
- Automatic notifications for booking and payment status changes, plus manual admin-created notifications.
- SQLite database and Bootstrap 5 CDN styling.

## Booking Flow

`Requested -> Pending -> Approved -> Payment Pending -> Confirmed -> Active Rental -> Completed`

The system also supports `Rejected` and `Cancelled`.

## Quick Start

Install Python 3.12 or newer first. On Windows, enable **Add Python to PATH** during installation.

```powershell
cd "C:\Users\USER\OneDrive\Desktop\AI Workshop"
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

If `py -3` is not available, use:

```powershell
python -m venv .venv
```

Open the app:

- Customer dashboard: `http://127.0.0.1:8000/customer/`
- Rental admin dashboard: `http://127.0.0.1:8000/admin/`
- Raw Django admin fallback: `http://127.0.0.1:8000/django-admin/`

The root URL redirects by role. Staff/admin accounts go to `/admin/`; customer accounts go to `/customer/`.
Customer pages are for non-staff customer accounts only.

Demo credentials created by `seed_demo`:

- Admin: `admin` / `Admin@12345`
- Customer: `customer` / `Customer@12345`

You can also create your own admin account:

```powershell
python manage.py createsuperuser
```

## Manual Payment Workflow

1. Customer requests a booking from Browse Bikes.
2. Admin reviews the booking in the rental admin dashboard.
3. Admin approves the booking or marks it payment pending from the admin dashboard.
4. Customer visits the office and pays cash.
5. Admin confirms the cash payment from the Payments screen.
6. The payment becomes verified and the booking becomes confirmed.

## Google Login Setup

The login and register screens include **Continue with Google** for customers. The button is disabled until Google OAuth credentials are added.

1. Create OAuth credentials in Google Cloud Console.
2. Add this redirect URI:

```text
http://127.0.0.1:8000/accounts/google/login/callback/
```

3. Open `http://127.0.0.1:8000/django-admin/`.
4. Go to **Social applications** and add a new app:
   - Provider: `Google`
   - Name: `Google`
   - Client id: your Google client ID
   - Secret key: your Google client secret
   - Sites: move `127.0.0.1:8000` to chosen sites
5. Save, then refresh `http://127.0.0.1:8000/login/`.

Google-created users automatically get a customer profile.

## Useful Commands

```powershell
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

The `seed_demo` command resets the demo customer's bookings, documents, and notifications so the sample dashboard stays consistent.
