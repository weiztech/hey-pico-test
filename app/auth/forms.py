from django import forms

from .models import AccessToken


class AccessTokenAdminForm(forms.ModelForm):
    class Meta:
        model = AccessToken
        fields = "__all__"
