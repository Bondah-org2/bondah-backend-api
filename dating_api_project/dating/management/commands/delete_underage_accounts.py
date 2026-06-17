import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

User = get_user_model()


class Command(BaseCommand):
    help = "Delete flagged underage accounts past their scheduled deletion time"

    def handle(self, *args, **options):
        users = User.objects.filter(
            is_flagged_for_deletion=True,
            scheduled_deletion_at__lte=timezone.now()
        )

        count = users.count()

        for user in users:
            self.stdout.write(f"Deleting underage account: {user.email}")
            logger.info(f"Deleting underage account: {user.email} (id={user.id})")
            user.delete()

        self.stdout.write(
            self.style.SUCCESS(f"Deleted {count} underage account(s).")
        )
        logger.info(f"delete_underage_accounts: removed {count} account(s).")

        