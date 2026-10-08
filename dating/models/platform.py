from django.core.cache import cache
from django.core.validators import MaxValueValidator
from django.db import models

PLATFORM_SETTINGS_CACHE_KEY = "platform_settings:v1"


class PlatformSettings(models.Model):
    """Business numbers Team Bondah can change in admin without a deploy.

    Always a single row (pk=1). Read it through `PlatformSettings.current()`,
    which is cached and refreshed whenever the row is saved.
    """

    gift_conversion_percent = models.PositiveSmallIntegerField(
        default=70,
        validators=[MaxValueValidator(100)],
        help_text="Share of a gift's coin cost the recipient gets when converting it to coins.",
    )

    # Withdrawals stay closed until Team Bondah sets the rate and the minimum.
    coin_cash_rate_usd = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True,
        help_text="US dollars paid out per earned coin.",
    )
    min_withdrawal_coins = models.PositiveIntegerField(
        null=True, blank=True, help_text="Smallest withdrawal, in coins.",
    )
    withdrawal_fee_usd = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        help_text="Taken from each withdrawal's cash amount.",
    )

    updated_at = models.DateTimeField(auto_now=True)

    @property
    def withdrawals_open(self) -> bool:
        return bool(self.coin_cash_rate_usd and self.coin_cash_rate_usd > 0 and self.min_withdrawal_coins)

    class Meta:
        verbose_name = "Platform settings"
        verbose_name_plural = "Platform settings"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(gift_conversion_percent__lte=100),
                name="platform_gift_conversion_percent_max_100",
            ),
        ]

    def __str__(self):
        return "Platform settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete(PLATFORM_SETTINGS_CACHE_KEY)

    def delete(self, *args, **kwargs):
        # The row is required; deleting it is never what admin wants.
        return 0, {}

    @classmethod
    def current(cls) -> "PlatformSettings":
        settings_row = cache.get(PLATFORM_SETTINGS_CACHE_KEY)
        if settings_row is None:
            settings_row, _ = cls.objects.get_or_create(pk=1)
            cache.set(PLATFORM_SETTINGS_CACHE_KEY, settings_row, 300)
        return settings_row
