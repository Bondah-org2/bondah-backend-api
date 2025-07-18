from django.urls import path
from .views import (
    UserCreateView, 
    NewsletterSignupView, 
    GetPuzzleView, SubmitPuzzleAnswerView, 
    EarnCoinsView, 
    SpendCoinsView,
)

urlpatterns = [
    path('create-user/', UserCreateView.as_view(), name='create-user'),
    path('newsletter/signup/', NewsletterSignupView.as_view(), name='newsletter-signup'),
    path('puzzle/', GetPuzzleView.as_view(), name='get-puzzle'),
    path('puzzle/verify/', SubmitPuzzleAnswerView.as_view(), name='verify-puzzle'),
    path('coins/earn/', EarnCoinsView.as_view(), name='earn-coins'),
    path('coins/spend/', SpendCoinsView.as_view(), name='spend-coins'),
]