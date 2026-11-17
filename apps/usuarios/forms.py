from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import Usuario


class UsuarioCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ("email", "nome", "perfil", "nivel")


class UsuarioChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = Usuario
        fields = "__all__"
