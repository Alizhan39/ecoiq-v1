from django import forms
from django.contrib.auth import get_user_model

from financial_intelligence_cloud.models import (
    ClientPayment, ClientReminder, ClientService, PortfolioEntity,
)


class AccountScopedFormMixin:
    """Keep every selectable row inside the accounting firm's own client book."""

    def __init__(self, *args, institutional_account=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.institutional_account = institutional_account
        if not institutional_account:
            return
        clients = PortfolioEntity.objects.filter(portfolio__institutional_account=institutional_account)
        if 'client' in self.fields:
            self.fields['client'].queryset = clients
        if 'client_service' in self.fields:
            self.fields['client_service'].queryset = ClientService.objects.filter(
                client__portfolio__institutional_account=institutional_account,
            ).select_related('client', 'service')
        if 'service' in self.fields:
            self.fields['service'].queryset = institutional_account.accounting_services.filter(is_active=True)
        if 'assigned_to' in self.fields:
            self.fields['assigned_to'].queryset = get_user_model().objects.filter(is_staff=True, is_active=True)
        if 'owner' in self.fields:
            self.fields['owner'].queryset = get_user_model().objects.filter(is_staff=True, is_active=True)


class ClientReminderForm(AccountScopedFormMixin, forms.ModelForm):
    class Meta:
        model = ClientReminder
        fields = ('client', 'client_service', 'owner', 'title', 'due_at', 'priority', 'notes')
        widgets = {
            'due_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def clean(self):
        cleaned = super().clean()
        client = cleaned.get('client')
        engagement = cleaned.get('client_service')
        if engagement and client and engagement.client_id != client.pk:
            self.add_error('client_service', 'The selected service belongs to a different client.')
        if engagement and not client:
            cleaned['client'] = engagement.client
        if not cleaned.get('client') and not engagement:
            self.add_error('client', 'Choose a client or a client service.')
        return cleaned


class ClientServiceForm(AccountScopedFormMixin, forms.ModelForm):
    class Meta:
        model = ClientService
        fields = (
            'client', 'service', 'assigned_to', 'status', 'start_date',
            'next_due_date', 'agreed_fee', 'currency', 'notes',
        )
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'next_due_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def clean(self):
        cleaned = super().clean()
        client = cleaned.get('client')
        service = cleaned.get('service')
        if client and service:
            client_account_id = client.portfolio.institutional_account_id
            if client_account_id != service.institutional_account_id:
                self.add_error('service', 'The service and client must belong to the same firm.')
        return cleaned


class ClientPaymentForm(AccountScopedFormMixin, forms.ModelForm):
    class Meta:
        model = ClientPayment
        fields = ('client_service', 'amount_due', 'currency', 'due_date', 'payment_method', 'reference', 'notes')
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class RecordPaymentForm(forms.Form):
    amount_received = forms.DecimalField(min_value=0.01, max_digits=12, decimal_places=2)
    payment_method = forms.CharField(max_length=80, required=False)
    reference = forms.CharField(max_length=160, required=False)

    def __init__(self, *args, payment=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.payment = payment

    def clean_amount_received(self):
        amount = self.cleaned_data['amount_received']
        if self.payment and amount > self.payment.balance:
            raise forms.ValidationError(f'Amount exceeds the outstanding balance ({self.payment.balance}).')
        return amount
