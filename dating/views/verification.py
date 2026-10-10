from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from ..models import DocumentVerification, SelfieVerification
from ..serializers import DocumentVerificationCreateSerializer, DocumentVerificationSerializer, SelfieSubmissionSerializer, DocumentVerificationListSerializer
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView


# =============================================================================
# DOCUMENT VERIFICATION VIEWS (NEW FROM FIGMA)
# =============================================================================
@extend_schema(
    tags=["DocumentVerification"],
    )
class DocumentVerificationListView(generics.ListCreateAPIView):
    """
    List and create document verification requests
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":

            return DocumentVerificationCreateSerializer

        return DocumentVerificationListSerializer

    def get_queryset(self):

        return DocumentVerification.objects.filter(user=self.request.user)


@extend_schema(
    tags=["DocumentVerification"],
    )
class DocumentVerificationDetailView(generics.RetrieveAPIView):
    """
    Retrieve one of my document verifications.

    Read-only: a submitted ID can't be swapped or deleted. To fix one, Team
    Bondah asks for a new scan and the app uploads a new document.
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        return DocumentVerificationSerializer

    def get_queryset(self):
        from ..models import DocumentVerification

        return DocumentVerification.objects.filter(user=self.request.user)


@extend_schema(
    tags=["Upload"],
    )
class SelfieSubmissionView(GenericAPIView):
    serializer_class = SelfieSubmissionSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        selfie = serializer.save()

        return Response(
            {
                "message": "Selfie submitted successfully",
                "data": {
                    "id": selfie.id,
                    "status": selfie.status,
                    "selfie_image_url": selfie.selfie_image_url,
                    "document_verification_id": selfie.document_verification.id
                },
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    tags=["Upload"],
    )
class UserSelfieListView(generics.ListAPIView):
    serializer_class = SelfieSubmissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SelfieVerification.objects.filter(user=self.request.user)
