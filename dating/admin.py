from django.contrib import admin
from .models import User, NewsletterSubscriber, PuzzleVerification, CoinTransaction

# Register your models here.

admin.site.register(User)
admin.site.register(NewsletterSubscriber)
admin.site.register(PuzzleVerification)
admin.site.register(CoinTransaction)
