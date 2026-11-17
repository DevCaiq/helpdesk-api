from django.contrib.auth.base_user import BaseUserManager


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    @classmethod
    def normalize_email(cls, email):
        return super().normalize_email(email).strip().lower()

    def get_by_natural_key(self, email):
        return self.get(email__iexact=email.strip())

    def create_user(self, email, password=None, **extra_fields):
        if not email or not email.strip():
            raise ValueError("O e-mail é obrigatório.")
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.full_clean()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        if not password:
            raise ValueError("Superusuário exige senha.")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("perfil", "GESTOR")
        if extra_fields["is_staff"] is not True or extra_fields["is_superuser"] is not True:
            raise ValueError("Superusuário exige is_staff=True e is_superuser=True.")
        return self.create_user(email, password, **extra_fields)
