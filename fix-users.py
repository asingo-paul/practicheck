import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "practicheck.settings")  # adjust if your settings file path differs
django.setup()

from accounts.models import User

def fix_user_types():
    users = User.objects.all()
    for user in users:
        # If somehow stored as string, cast to int
        if isinstance(user.user_type, str):
            try:
                corrected_type = int(user.user_type)
                user.user_type = corrected_type
                user.save()
                print(f"Fixed {user.username}: user_type -> {corrected_type}")
            except ValueError:
                print(f"Skipping {user.username}: invalid user_type {user.user_type}")
        else:
            # Already integer, nothing to fix
            pass

if __name__ == "__main__":
    fix_user_types()
