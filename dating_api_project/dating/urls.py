from django.urls import path, include
from . import liveness_views
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter
from .views import (
    NewsletterSignupView,
    GetPuzzleView,
    SubmitPuzzleAnswerView,
    # EarnCoinsView,
    # SpendCoinsView,
    JoinWaitlistView,
    SendNewsletterWelcomeEmailView,
    SendWaitlistConfirmationEmailView,
    SendGenericEmailView,
    # JobListView,
    # JobDetailView,
    # JobApplicationView,
    # JobOptionsView,
    AdminLoginView,
    UpdateAdminMemberView,
    RemoveAdminMemberView,
    CreateAdminMemberView,
    AdminTeamView,
    # AdminJobListView,
    # AdminJobCreateView,
    # AdminJobUpdateView,
    # AdminJobApplicationsView,
    # AdminJobApplicationDetailView,
    # AdminUpdateApplicationStatusView,
    AdminWaitlistListView,
    AdminNewsletterListView,
    AdminLogoutView,
    TranslationView,
    # SupportedLanguagesView,
    TranslationHistoryView,
    TranslationStatsView,
    # Mobile App Authentication Views
    UserLoginView,
    UserLogoutView,
    TokenRefreshView,
    PasswordResetView,
    PasswordResetConfirmView,
    UserProfileViews,
    AccountDeactivationView,
    NotificationSettingsView,
    LanguageSettingsView,
    DeviceRegistrationView,
    # OAuth Views
    GoogleOAuthView,
    AppleOAuthView,
    SocialLoginView,
    OAuthLinkAccountView,
    OAuthUnlinkAccountView,
    SocialAccountsListView,
    # Location Management Views
    LocationUpdateView,
    AddressGeocodeView,
    LocationPrivacyUpdateView,
    LocationPermissionsView,
    LocationHistoryView,
    NearbyUsersView,
    MatchPreferencesView,
    UserLocationProfileView,
    LocationStatisticsView,
    # Email and Phone Verification Views
    RegisterRequestOTPView,
    ResendEmailOTPView,
    RegisterRequestOTPView,
    UserRoleSelectionView,
    # Advanced Search and Discovery Views
    # UserSearchView,
    UserProfileDetailView,
    UserInteractionView,
    # UserRecommendationsView,
    # CategoryFilterView,
    UserInterestsView,
    # Chat and Messaging Views (NEW)
    ChatListView,
    ChatDetailView,
    SendMessageView,
    # MessageListView,
    # MessageDetailView,
    # CallInitiateView,
    # CallAnswerView,
    # CallEndView,
    # ChatReportView,
    # MatchmakerIntroView,
    # Social Feed and Story Views (NEW)
    # PostCommentListView,
    # PostReportView,
    # PostShareView,
    StoryViewSet,
    # FeedSearchView,
    # FeedSuggestionsView,
    # Live Session Views (NEW)
    # LiveSessionListView,
    # LiveSessionDetailView,
    # LiveSessionJoinView,
    # LiveSessionLeaveView,
    # New Figma Features
    # UserSocialHandleListView,
    # UserSocialHandleDetailView,
    # UserSecurityQuestionListView,
    # UserSecurityQuestionDetailView,
    DocumentVerificationListView,
    DocumentVerificationDetailView,
    # DocumentUploadView,
    # CreateUsernameView,
    UsernameUpdateView,
    # Subscription Plans Views (NEW FROM FIGMA)
    SubscriptionPlanListView,
    UserSubscriptionListView,
    UserSubscriptionDetailView,
    UserCurrentSubscriptionView,
    UserFeatureAccessView,
    # Bondcoin Wallet Views (NEW FROM FIGMA)
    BondcoinPackageListView,
    BondcoinTransactionListView,
    MyWalletView,
    MyLedgerView,
    # Virtual Gifting Views (NEW FROM FIGMA)
    GiftCategoryListView,
    VirtualGiftListView,
    VirtualGiftDetailView,
    ConvertGiftView,
    SendGiftView,
    # Live Streaming Enhancement Views (NEW FROM FIGMA)
    LiveGiftListView,
    LiveJoinRequestListView,
    LiveJoinRequestDetailView,
    LiveJoinRequestManageView,
    LiveSessionGiftersView,
    PaymentMethodListView,
    PaymentTransactionListView,
    PaymentTransactionDetailView,
    ProcessPaymentView,
    PaymentWebhookView,
    RefundPaymentView,
    # Firebase Integration Views
    # FirebaseLoginView,
    # FirebaseUserProfileView,
    # FirebaseMatchView,
    # FirebaseMatchesListView,
    # FirebasePushNotificationView,
    AdminBondmakerReviewView,
    AdminPendingBondmakersView,
    UserRoleStatusView,
    AdminBondmakerListView,
    PublicBondmakerListView,
    BondmakerProfileDetailView,
    SubscribeBondmakerView,
    EndBondmakerSubscriptionView,
    AllSubscribedUsersListView,
    SubscribedUsersForBondmakerView,
    # BondmakerMatchCreateView,
    BondmakerSuggestionView,
    SetVisibilityView,
    EndVisbilityView,
    GlobalPublicUsersListView,
    PrivateUsersForBondmakerListView,
    MatchRequestCreateView,
    PurchaseCoinView,
    BondmakerMatchActionView,
    PasswordResendOTPView,
    PasswordResetVerifyOTPView,
    PasswordResetConfirmView,
    UserSwipeDeckView,
    BondmakerPendingMatchListView,
    BondmakerProfileUpdateView,
    VerifyOTPView,
    ConfirmRegistrationView,
    ApproveVisibilityView,
    PendingVisibilityListView,
    BondmakerSearchView,
    BondmakerSpecialisationView,
    SpecialisationCategoryListView,
    BondmakerDashboardView,
    BondmakerAnalyticsView,
    VisibilityStatusView,
    UserMatchedListView,
    IncomingPendingMatchListView,
    SuggestedMatchView,
    BondCircleCreateView,
    AddBondCircleMembersView,
    BondCirclePostCreateView,
    BondCircleFeedView,
    TogglePostLikeView,
    BondmakerAcceptedMatchesView,
    CreateCommentView,
    PostViewSet,
    PostCommentViewSet,
    AdminOverviewView,
    CloudinarySignatureView,
    ChatMessagesView,
    SelfieSubmissionView,
    UserSelfieListView,
    GoogleOAuthCallbackView,
)
from .liveness_views import (
    StartLivenessCheckView,
    SubmitLivenessImagesView,
    SubmitLivenessVideoView,
    LivenessCheckStatusView,
    RetryLivenessCheckView,
    UserVerificationStatusView
)

router = DefaultRouter()
router.register(r"bondstory/posts", PostViewSet, basename="bondstory-posts")
router.register(r"stories", StoryViewSet, basename="stories")

# Nested router for comments under posts
posts_router = NestedDefaultRouter(router, r"bondstory/posts", lookup="post")  # lookup='post' ensures post_pk
posts_router.register(r"bondstory/comments", PostCommentViewSet, basename="post-comments")


urlpatterns = [
    # Public API endpoints
    # path("create-user/", UserCreateView.as_view(), name="create-user"),
    path(
        "newsletter/signup/", NewsletterSignupView.as_view(), name="newsletter-signup"
    ),
    path(
        "newsletter/subscribe/",
        NewsletterSignupView.as_view(),
        name="newsletter-subscribe",
    ),
    path("puzzle/", GetPuzzleView.as_view(), name="get-puzzle"),
    path("puzzle/verify/", SubmitPuzzleAnswerView.as_view(), name="verify-puzzle"),
    # path("coins/earn/", EarnCoinsView.as_view(), name="earn-coins"),
    # path("coins/spend/", SpendCoinsView.as_view(), name="spend-coins"),
    path("waitlist/", JoinWaitlistView.as_view(), name="join-waitlist"),
    path(
        "email/send-newsletter-welcome/",
        SendNewsletterWelcomeEmailView.as_view(),
        name="send-newsletter-welcome",
    ),
    path(
        "email/send-waitlist-confirmation/",
        SendWaitlistConfirmationEmailView.as_view(),
        name="send-waitlist-confirmation",
    ),
    path("email/send/", SendGenericEmailView.as_view(), name="send-generic-email"),
    # path("jobs/", JobListView.as_view(), name="job-list"),
    # path("jobs/<int:id>/", JobDetailView.as_view(), name="job-detail"),
    # path("jobs/apply/", JobApplicationView.as_view(), name="job-application"),
    # path("jobs/options/", JobOptionsView.as_view(), name="job-options"),
    # # Translation API endpoints
    # path("translate/", TranslationView.as_view(), name="translate"),
    path(
        "translate/languages/",
        TranslationView.as_view(),
        name="supported-languages",
    ),
    path(
        "translate/history/",
        TranslationHistoryView.as_view(),
        name="translation-history",
    ),
    path("translate/stats/", TranslationStatsView.as_view(), name="translation-stats"),
    # Admin API endpoints
    path("admin/login/", AdminLoginView.as_view(), name="admin-login"),
    path(
        "principal/token/refresh/",
        TokenRefreshView.as_view(),
        name="token-refresh"
    ),
    path("admin/logout/", AdminLogoutView.as_view(), name="admin-logout"),
    path(
        "admin/members/<int:pk>/update/",
        UpdateAdminMemberView.as_view(),
        name="update-team-member"
    ),
    path(
        "admin/team/<int:pk>/delete/",
        RemoveAdminMemberView.as_view(),
        name="delete-team-member"
    ),
    path(
        "admin/member/create/",
        CreateAdminMemberView.as_view(),
        name="create-team-member"
    ),
    path(
        "admin/team/",
        AdminTeamView.as_view(),
        name="team-list"
    ),
    # path("admin/jobs/", AdminJobListView.as_view(), name="admin-job-list"),
    # path("admin/jobs/create/", AdminJobCreateView.as_view(), name="admin-job-create"),
    # path(
    #     "admin/jobs/<int:job_id>/update/",
    #     AdminJobUpdateView.as_view(),
    #     name="admin-job-update",
    # ),
    # path(
    #     "admin/applications/",
    #     AdminJobApplicationsView.as_view(),
    #     name="admin-applications",
    # ),
    # path(
    #     "admin/applications/<int:application_id>/",
    #     AdminJobApplicationDetailView.as_view(),
    #     name="admin-application-detail",
    # ),
    # path(
    #     "admin/applications/<int:application_id>/status/",
    #     AdminUpdateApplicationStatusView.as_view(),
    #     name="admin-update-application-status",
    # ),
    path(
        "admin/waitlist/", AdminWaitlistListView.as_view(), name="admin-waitlist-list"
    ),
    path(
        "admin/newsletter/",
        AdminNewsletterListView.as_view(),
        name="admin-newsletter-list",
    ),

    # Admin OverView
    path("admin/overview/", AdminOverviewView.as_view(), name="admin-overview"),

    # Mobile App Authentication Endpoints
    path(
        "auth/register/request-otp//",
        RegisterRequestOTPView.as_view(),
        name="request-email-otp",
    ),
    path(
        "auth/register/resend-otp/",
        ResendEmailOTPView.as_view(),
        name="resend-email-otp",
    ),
    path(
        "auth/register/confirm/",
        ConfirmRegistrationView.as_view(),
        name="confirm - signin",
    ),
    path(
        "auth/register/verify-otp/",
        VerifyOTPView.as_view(),
        name="verify-email-otp",
    ),
    path("auth/login/", UserLoginView.as_view(), name="user-login"),
    path("auth/logout/", UserLogoutView.as_view(), name="user-logout"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/password-reset/", PasswordResetView.as_view(), name="password-reset"),
    path(
        "auth/password-reset-confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path(
        "auth/password-reset-otp-verify/",
        PasswordResetVerifyOTPView.as_view(),
        name="password-reset-verify",
    ),
    path("auth/password/reset/resend-otp/", PasswordResendOTPView.as_view()),
    path("auth/profile/", UserProfileViews.as_view(), name="user-profile"),
    path(
        "auth/deactivate/account", AccountDeactivationView.as_view(), name="account-deactivate"
    ),
    path(
        "auth/notifications/",
        NotificationSettingsView.as_view(),
        name="notification-settings",
    ),
    path("auth/language/", LanguageSettingsView.as_view(), name="language-settings"),
    path(
        "auth/device-register/",
        DeviceRegistrationView.as_view(),
        name="device-register",
    ),
    # OAuth Authentication Endpoints
    path("oauth/google/", GoogleOAuthView.as_view(), name="google-oauth"),
    path("oauth/google/callback/", GoogleOAuthCallbackView.as_view(), name="google-callback"),
    path("oauth/apple/", AppleOAuthView.as_view(), name="apple-oauth"),
    path("oauth/social-login/", SocialLoginView.as_view(), name="social-login"),
    path(
        "oauth/link-account/", OAuthLinkAccountView.as_view(), name="oauth-link-account"
    ),
    path(
        "oauth/unlink-account/<str:provider>/",
        OAuthUnlinkAccountView.as_view(),
        name="oauth-unlink-account",
    ),
    path(
        "oauth/social-accounts/",
        SocialAccountsListView.as_view(),
        name="social-accounts-list",
    ),
    # Liveness Check / Facial Verification Endpoints
    path(
        "liveness/start/",
        StartLivenessCheckView.as_view(),
        name="liveness-start",
    ),
    path(
        "liveness/submit/video/",
        SubmitLivenessVideoView.as_view(),
        name="liveness-submit-video",
    ),
    path(
        "liveness/submit/images/",
        SubmitLivenessImagesView.as_view(),
        name="liveness-submit-images",
    ),
    path(
        "liveness/status/<str:session_id>/",
        LivenessCheckStatusView.as_view(),
        name="liveness-status",
    ),
    path(
        "liveness/retry/",
        RetryLivenessCheckView.as_view(),
        name="liveness-retry",
    ),
    path(
        "liveness/verification/status/",
        UserVerificationStatusView.as_view(),
        name="verification-status",
    ),

    # Users Role selection EndPoint
    path(
        "roleselection/role/",
        UserRoleSelectionView.as_view(),
        name="user-role-selection",
    ),
    # Advanced Search and Discovery Endpoints
    # path("search/users/", UserSearchView.as_view(), name="user-search"),
    path(
        "auth/<int:user_id>/profile-detail/",
        UserProfileDetailView.as_view(),
        name="user-profile-detail",
    ),
    path("users/interact/", UserInteractionView.as_view(), name="user-interaction"),
    # path(
    #     "users/recommendations/",
    #     UserRecommendationsView.as_view(),
    #     name="user-recommendations",
    # ),
    # path("users/category/", CategoryFilterView.as_view(), name="category-filter"),
    path("users/interests/", UserInterestsView.as_view(), name="user-interests"),
    # Location Management Endpoints
    path("location/update/", LocationUpdateView.as_view(), name="location-update"),
    path("location/geocode/", AddressGeocodeView.as_view(), name="address-geocode"),
    path(
        "location/privacy/",
        LocationPrivacyUpdateView.as_view(),
        name="location-privacy",
    ),
    path(
        "location/permissions/",
        LocationPermissionsView.as_view(),
        name="location-permissions",
    ),
    path("location/history/", LocationHistoryView.as_view(), name="location-history"),
    path("location/nearby-users/", NearbyUsersView.as_view(), name="nearby-users"),
    path(
        "location/match-preferences/",
        MatchPreferencesView.as_view(),
        name="match-preferences",
    ),
    path(
        "location/profile/",
        UserLocationProfileView.as_view(),
        name="user-location-profile",
    ),
    path(
        "location/statistics/",
        LocationStatisticsView.as_view(),
        name="location-statistics",
    ),
    # Chat and Messaging Endpoints (NEW)
    # path("chat/", ChatListView.as_view(), name="chat-list"),
    # path("chat/<int:pk>/", ChatDetailView.as_view(), name="chat-detail"),
    # path(
    #     "chat/<int:chat_id>/messages/", MessageListView.as_view(), name="message-list"
    # ),
    # path(
    #     "chat/<int:chat_id>/messages/<int:pk>/",
    #     MessageDetailView.as_view(),
    #     name="message-detail",
    # ),
    # path("chat/<int:chat_id>/report/", ChatReportView.as_view(), name="chat-report"),
    # path(
    #     "chat/<int:chat_id>/messages/<int:message_id>/report/",
    #     ChatReportView.as_view(),
    #     name="message-report",
    # ),
    # path(
    #     "chat/matchmaker-intro/", MatchmakerIntroView.as_view(), name="matchmaker-intro"
    # ),
    # # Voice/Video Call Endpoints (NEW)
    # path("calls/initiate/", CallInitiateView.as_view(), name="call-initiate"),
    # path("calls/<str:call_id>/answer/", CallAnswerView.as_view(), name="call-answer"),
    # path("calls/<str:call_id>/end/", CallEndView.as_view(), name="call-end"),
    # Social Feed and Story Endpoints (NEW)
    # path(
    #     "feed/posts/<int:post_id>/report/", PostReportView.as_view(), name="post-report"
    # ),
    # path(
    #     "feed/comments/<int:comment_id>/report/",
    #     PostReportView.as_view(),
    #     name="comment-report",
    # ),
    # path("feed/search/", FeedSearchView.as_view(), name="feed-search"),
    # path("feed/suggestions/", FeedSuggestionsView.as_view(), name="feed-suggestions"),
    # # Live Session Endpoints (NEW)
    # path("live-sessions/", LiveSessionListView.as_view(), name="live-session-list"),
    # path(
    #     "live-sessions/<int:pk>/",
    #     LiveSessionDetailView.as_view(),
    #     name="live-session-detail",
    # ),
    # path(
    #     "live-sessions/<int:session_id>/join/",
    #     LiveSessionJoinView.as_view(),
    #     name="live-session-join",
    # ),
    # path(
    #     "live-sessions/<int:session_id>/leave/",
    #     LiveSessionLeaveView.as_view(),
    #     name="live-session-leave",
    # ),
    # Social Media Handles Endpoints (NEW FROM FIGMA)
    # path(
    #     "social-handles/", UserSocialHandleListView.as_view(), name="social-handle-list"
    # ),
    # path(
    #     "social-handles/<int:pk>/",
    #     UserSocialHandleDetailView.as_view(),
    #     name="social-handle-detail",
    # ),
    # # Security Questions Endpoints (NEW FROM FIGMA)
    # path(
    #     "security-questions/",
    #     UserSecurityQuestionListView.as_view(),
    #     name="security-question-list",
    # ),
    # path(
    #     "security-questions/<int:pk>/",
    #     UserSecurityQuestionDetailView.as_view(),
    #     name="security-question-detail",
    # ),
    # Document Verification Endpoints (NEW FROM FIGMA)
    path(
        "document-verification/",
        DocumentVerificationListView.as_view(),
        name="document-verification-list",
    ),
    path(
        "document-verification/<int:pk>/",
        DocumentVerificationDetailView.as_view(),
        name="document-verification-detail",
    ),

    # Username Validation Endpoints (NEW FROM FIGMA)
    # path("username/create/", CreateUsernameView.as_view(), name="username-validate"),
    path("username/update/", UsernameUpdateView.as_view(), name="username-update"),
    # Subscription Plans Endpoints (NEW FROM FIGMA)
    path(
        "subscriptions/plans/",
        SubscriptionPlanListView.as_view(),
        name="subscription-plans",
    ),
    path(
        "subscriptions/", UserSubscriptionListView.as_view(), name="user-subscriptions"
    ),
    path(
        "subscriptions/<int:pk>/",
        UserSubscriptionDetailView.as_view(),
        name="user-subscription-detail",
    ),
    path(
        "subscriptions/current/",
        UserCurrentSubscriptionView.as_view(),
        name="current-subscription",
    ),
    path(
        "subscriptions/feature-access/",
        UserFeatureAccessView.as_view(),
        name="feature-access",
    ),
    # Bondcoin package List View
    path(
        "bondcoin/packages/",
        BondcoinPackageListView.as_view(),
        name="bondcoin-packages",
    ),
    # Bondcoin Transaction List View
    path(
        "bondcoin/transactions/",
        BondcoinTransactionListView.as_view(),
        name="bondcoin-transactions",
    ),
    # path(
    #     "bondcoin/transactions/<int:pk>/",
    #     BondcoinTransactionDetailView.as_view(),
    #     name="bondcoin-transaction-detail",
    # ),
    # path(
    #     "bondcoin/purchase/", BondcoinPurchaseView.as_view(), name="bondcoin-purchase"
    # ),
    # Virtual Gifting Endpoints (NEW FROM FIGMA)
    path("gifts/categories/", GiftCategoryListView.as_view(), name="gift-categories"),
    path("gifts/", VirtualGiftListView.as_view(), name="virtual-gifts"),
    path(
        "gifts/<int:pk>/", VirtualGiftDetailView.as_view(), name="virtual-gift-detail"
    ),
    # Live Streaming Enhancement Endpoints (NEW FROM FIGMA)
    path("live-sessions/gifts/", LiveGiftListView.as_view(), name="live-gifts"),
    path(
        "live-sessions/join-requests/",
        LiveJoinRequestListView.as_view(),
        name="live-join-requests",
    ),
    path(
        "live-sessions/join-requests/<int:pk>/",
        LiveJoinRequestDetailView.as_view(),
        name="live-join-request-detail",
    ),
    path(
        "live-sessions/join-requests/<int:pk>/manage/",
        LiveJoinRequestManageView.as_view(),
        name="live-join-request-manage",
    ),
    path(
        "live-sessions/<int:session_id>/gifters/",
        LiveSessionGiftersView.as_view(),
        name="live-session-gifters",
    ),
    # Payment Processing Endpoints
    path("payments/methods/", PaymentMethodListView.as_view(), name="payment-methods"),
    path(
        "payments/transactions/",
        PaymentTransactionListView.as_view(),
        name="payment-transactions",
    ),
    path(
        "payments/transactions/<int:pk>/",
        PaymentTransactionDetailView.as_view(),
        name="payment-transaction-detail",
    ),
    path("payments/process/", ProcessPaymentView.as_view(), name="process-payment"),
    path(
        "payments/webhooks/<str:provider>/",
        PaymentWebhookView.as_view(),
        name="payment-webhook",
    ),
    path(
        "payments/refund/<int:transaction_id>/",
        RefundPaymentView.as_view(),
        name="refund-payment",
    ),
    # Firebase Integration Endpoints
    # path("firebase/login/", FirebaseLoginView.as_view(), name="firebase-login"),
    # path(
    #     "firebase/profile/", FirebaseUserProfileView.as_view(), name="firebase-profile"
    # ),
    # path("firebase/match/", FirebaseMatchView.as_view(), name="firebase-match"),
    # path(
    #     "firebase/matches/", FirebaseMatchesListView.as_view(), name="firebase-matches"
    # ),
    # path(
    #     "firebase/notify/",
    #     FirebasePushNotificationView.as_view(),
    #     name="firebase-notify",
    # ),
    path(
        "admin/bondmakers/review/<int:verification_id>/",
        AdminBondmakerReviewView.as_view(),
        name="bondmaker-review",
    ),
    path(
        "admin/bondmakers/pending_list/",
        AdminPendingBondmakersView.as_view(),
        name="bondmaker-pennding_list",
    ),
    path("user/role-status/", UserRoleStatusView.as_view(), name="role_status"),
    path(
        "admin/bondmakers/",
        AdminBondmakerListView.as_view(),
        name="admin-bondmaker-list",
    ),
    # List all public bondmakers
    path(
        "bondmaker/list/",
        PublicBondmakerListView.as_view(),
        name="public-bondmaker-list",
    ),
    # Retrieve a single bondmaker profile by ID
    path(
        "bondmaker/<int:pk>/",
        BondmakerProfileDetailView.as_view(),
        name="bondmaker-profile-detail",
    ),
    # bondmaker Profile UpdateView
    path(
        "bondmaker/profile/update/",
        BondmakerProfileUpdateView.as_view(),
        name="bondmaker-profile-update",
    ),
    path(
        "bondmaker/subscribe/",
        SubscribeBondmakerView.as_view(),
        name="subscribe-bondmaker",
    ),
    path(
        "bondmaker/unsubscribe/<int:subscription_id>/",
        EndBondmakerSubscriptionView.as_view(),
        name="end-subscription",
    ),
    # List all users subscribed to all bondmaker
    path(
        "users/subscribed/",
        AllSubscribedUsersListView.as_view(),
        name="all-subscribed-users",
    ),
    # List all users subscribed to the logged-in bondmaker
    path(
        "bondmaker/subscribed-users/",
        SubscribedUsersForBondmakerView.as_view(),
        name="bondmaker-subscribed-users",
    ),
    # BONDMAKER MATCH SUGGESTION VIEW
    path(
        "bondmaker/suggest-match/",
        BondmakerSuggestionView.as_view(),
        name="match_suggest",
    ),
    # Start / set visibility with a bondmaker
    path(
        "visibility/",
        SetVisibilityView.as_view(),
        name="set-visibility",
    ),
    #  Bondmaker approves/rejects
    path(
        "visibility/<int:pk>/approve/reject",
        ApproveVisibilityView.as_view(),
        name="approve-visibility",
    ),
    # End current visibility
    path(
        "visibility/end/",
        EndVisbilityView.as_view(),
        name="end-visibility",
    ),
    # pending Visibility reqest List for bondmaker
    path(
        "visibility/pending/",
        PendingVisibilityListView.as_view(),
        name="pending-visibility-list",
    ),
    # Visibility Stautus View
    path(
        "visibility/status/",
        VisibilityStatusView.as_view(),
        name="visibility_status",
    ),
    # Public users (visible to everyone)
    path(
        "visibility/public/list/",
        GlobalPublicUsersListView.as_view(),
        name="public-users-list",
    ),
    # Private users for the logged-in bondmaker
    path(
        "visibility/private_list/",
        PrivateUsersForBondmakerListView.as_view(),
        name="private-users-list",
    ),
    # Bondcoin Wallet
    path("wallet/", MyWalletView.as_view(), name="my-wallet"),
    path("wallet/ledger/", MyLedgerView.as_view(), name="my-ledger"),
    # Match Request
    path(
        "match-request/",
        MatchRequestCreateView.as_view(),
        name="create-match-request",
    ),
    path(
        "match-requests/<int:match_request_id>/action/",
        BondmakerMatchActionView.as_view(),
        name="bondmaker-match-action",
    ),
    # Purchase coins
    path("wallet/purchase_coins/", PurchaseCoinView.as_view(), name="purchase-coins"),
    path("wallet/send-gift/", SendGiftView.as_view(), name="send-gift"),
    path("wallet/convert-gift/", ConvertGiftView.as_view(), name="convert-gift"),
    # Swipe View
    path("auth/swipe-deck/", UserSwipeDeckView.as_view(), name="user-swipe-deck"),
    # List of Pending Request to each Bondmaker
    path(
        "pending/matches_Request/List/",
        BondmakerPendingMatchListView.as_view(),
        name="bondmaker-pending-matches",
    ),
    path(
        "bondmakers/search/",
        BondmakerSearchView.as_view(),
        name="bondmaker-search",
    ),
    # Set bondmaker specialisations
    path(
        "bondmaker/specialisation/",
        BondmakerSpecialisationView.as_view(),
        name="set-bondmaker-specialisation",
    ),
    path(
        "bondmaker/specialisations/categories/",
        SpecialisationCategoryListView.as_view(),
        name="specialisation-categories",
    ),
    # Bondmaker dashboard
    path(
        "bondmaker/dashboard/",
        BondmakerDashboardView.as_view(),
        name="bondmaker-dashboard",
    ),
    path(
        "bondmaker/analytics/",
        BondmakerAnalyticsView.as_view(),
        name="bondmaker-dashboard",
    ),
    # List View For Matched_User for Users
    path(
        "matches/for-users/",
        UserMatchedListView.as_view(),
        name="user-matched-list",
    ),
    # Bondmaker: list accepted matches under them
    path(
        "bondmaker/matches/",
        BondmakerAcceptedMatchesView.as_view(),
        name="bondmaker-accepted-matches",
    ),
    # Pending Match Request list for user
    path(
        "user-match/pending-requests/",
        IncomingPendingMatchListView.as_view(),
        name="incoming-pending-matches",
    ),
    # suggested matches View from bondmaker
    path("suggest/match-list/", SuggestedMatchView.as_view(), name="suggested-match"),
    # ---------------------------
    # BondCircle Management
    # ---------------------------
    path(
        "bondcircle/create/", BondCircleCreateView.as_view(), name="bondcircle-create"
    ),
    path(
        "bondcircle/<int:circle_id>/add-members/",
        AddBondCircleMembersView.as_view(),
        name="bondcircle-add-members",
    ),
    # ---------------------------
    # Circle Posts
    # ---------------------------
    path(
        "bondcircle/<int:circle_id>/posts/",
        BondCirclePostCreateView.as_view(),
        name="bondcircle-post-create",
    ),
    path(
        "bondcircle/<int:circle_id>/feed/",
        BondCircleFeedView.as_view(),
        name="bondcircle-feed",
    ),
    # ---------------------------
    # Post Interactions
    # ---------------------------
    path(
        "bondcircle/posts/toggle-like/",
        TogglePostLikeView.as_view(),
        name="bondcircle-post-toggle-like",
    ),
    path(
        "bond-circle/posts/<int:post_id>/comments/",
        CreateCommentView.as_view(),
        name="create-bond-circle-comment",
    ),
    # Matched Chats
    path("chats/", ChatListView.as_view()),
    path("chats/<int:pk>/", ChatDetailView.as_view()),
    path("chats/<int:chat_id>/send/", SendMessageView.as_view()),
    path("chats/<int:chat_id>/messages/", ChatMessagesView.as_view()),

    # ViewSet for Post, Story for BondStory
    path("", include(router.urls)),
    path("", include(posts_router.urls)),

    # Cloudinary Signature request view
    path("cloudinary-signature/", CloudinarySignatureView.as_view(), name="cloudinary"),

    path("selfie/submit/", SelfieSubmissionView.as_view()),
    path("selfie/", UserSelfieListView.as_view()),

]
