from django.urls import path
from .views import (
    UserCreateView, 
    NewsletterSignupView, 
    GetPuzzleView, SubmitPuzzleAnswerView, 
    EarnCoinsView, 
    SpendCoinsView,
    JoinWaitlistView,
    SendNewsletterWelcomeEmailView,
    SendWaitlistConfirmationEmailView,
    SendGenericEmailView,
    JobListView,
    JobDetailView,
)

urlpatterns = [
    path('create-user/', UserCreateView.as_view(), name='create-user'),
    path('newsletter/signup/', NewsletterSignupView.as_view(), name='newsletter-signup'),
    path('newsletter/subscribe/', NewsletterSignupView.as_view(), name='newsletter-subscribe'),
    path('puzzle/', GetPuzzleView.as_view(), name='get-puzzle'),
    path('puzzle/verify/', SubmitPuzzleAnswerView.as_view(), name='verify-puzzle'),
    path('coins/earn/', EarnCoinsView.as_view(), name='earn-coins'),
    path('coins/spend/', SpendCoinsView.as_view(), name='spend-coins'),
    path('waitlist/', JoinWaitlistView.as_view(), name='join-waitlist'),
    path('email/send-newsletter-welcome/', SendNewsletterWelcomeEmailView.as_view(), name='send-newsletter-welcome'),
    path('email/send-waitlist-confirmation/', SendWaitlistConfirmationEmailView.as_view(), name='send-waitlist-confirmation'),
    path('email/send/', SendGenericEmailView.as_view(), name='send-generic-email'),
    path('jobs/', JobListView.as_view(), name='job-list'),
    path('jobs/<int:id>/', JobDetailView.as_view(), name='job-detail'),
]