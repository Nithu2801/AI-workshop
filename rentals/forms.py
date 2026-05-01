from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Bike, Customer, CustomerDocument, Notification


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    phone = forms.CharField(max_length=20)
    license_number = forms.CharField(max_length=60, required=False)
    address = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "license_number",
            "address",
            "password1",
            "password2",
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            Customer.objects.create(
                user=user,
                phone=self.cleaned_data["phone"],
                license_number=self.cleaned_data.get("license_number", ""),
                address=self.cleaned_data.get("address", ""),
            )
        return user


class BookingRequestForm(forms.Form):
    bike_id = forms.IntegerField(widget=forms.HiddenInput)
    pickup_datetime = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
        label="Pickup date and time",
    )
    return_datetime = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
        label="Return date and time",
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        required=False,
        label="Notes",
    )

    def clean(self):
        cleaned_data = super().clean()
        pickup = cleaned_data.get("pickup_datetime")
        return_at = cleaned_data.get("return_datetime")

        if pickup and pickup < timezone.now():
            self.add_error("pickup_datetime", "Pickup date and time cannot be in the past.")
        if pickup and return_at and return_at <= pickup:
            self.add_error("return_datetime", "Return date and time must be after pickup.")
        return cleaned_data


class CustomerDocumentForm(forms.ModelForm):
    class Meta:
        model = CustomerDocument
        fields = ["document_type", "file", "notes"]
        widgets = {
            "document_type": forms.Select(attrs={"class": "form-select"}),
            "file": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }


class BikeForm(forms.ModelForm):
    class Meta:
        model = Bike
        fields = [
            "name",
            "model",
            "number_plate",
            "description",
            "image",
            "daily_rate",
            "engine_cc",
            "fuel_type",
            "is_available",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "model": forms.TextInput(attrs={"class": "form-control"}),
            "number_plate": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "image": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "daily_rate": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "0.01"}),
            "engine_cc": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "fuel_type": forms.TextInput(attrs={"class": "form-control"}),
            "is_available": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "image": "Bike image",
        }


class NotificationForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = ["customer", "title", "message", "notification_type"]
        widgets = {
            "customer": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "message": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "notification_type": forms.Select(attrs={"class": "form-select"}),
        }


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()

    class Meta:
        model = Customer
        fields = ["first_name", "last_name", "email", "phone", "license_number", "address"]
        widgets = {
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "license_number": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].widget.attrs.update({"class": "form-control"})
        self.fields["last_name"].widget.attrs.update({"class": "form-control"})
        self.fields["email"].widget.attrs.update({"class": "form-control"})
        if self.instance and self.instance.user_id:
            self.fields["first_name"].initial = self.instance.user.first_name
            self.fields["last_name"].initial = self.instance.user.last_name
            self.fields["email"].initial = self.instance.user.email

    def save(self, commit=True):
        customer = super().save(commit=False)
        customer.user.first_name = self.cleaned_data["first_name"]
        customer.user.last_name = self.cleaned_data["last_name"]
        customer.user.email = self.cleaned_data["email"]
        if commit:
            customer.user.save()
            customer.save()
        return customer
