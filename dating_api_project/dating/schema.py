"""
Custom OpenAPI schema generation for Bondah Dating API
"""
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from rest_framework import status


class BondahSchemaMixin:
    """Mixin to provide consistent schema documentation across views"""
    
    @classmethod
    def get_success_response_examples(cls):
        """Get common success response examples"""
        return [
            OpenApiExample(
                'Success Response',
                summary='Standard success response',
                description='Standard format for successful API responses',
                value={
                    "message": "Operation completed successfully",
                    "status": "success",
                    "data": {}
                },
                status_codes=[str(status.HTTP_200_OK)]
            ),
            OpenApiExample(
                'Created Response',
                summary='Resource created successfully',
                description='Standard format for successful resource creation',
                value={
                    "message": "Resource created successfully",
                    "status": "success",
                    "data": {
                        "id": 1,
                        "created_at": "2024-01-01T00:00:00Z"
                    }
                },
                status_codes=[str(status.HTTP_201_CREATED)]
            )
        ]
    
    @classmethod
    def get_error_response_examples(cls):
        """Get common error response examples"""
        return [
            OpenApiExample(
                'Validation Error',
                summary='Input validation failed',
                description='Response when input data validation fails',
                value={
                    "message": "Validation failed",
                    "status": "error",
                    "errors": {
                        "field_name": ["This field is required."]
                    }
                },
                status_codes=[str(status.HTTP_400_BAD_REQUEST)]
            ),
            OpenApiExample(
                'Authentication Error',
                summary='Authentication required',
                description='Response when authentication is required but not provided',
                value={
                    "message": "Authentication credentials were not provided.",
                    "status": "error",
                    "code": "authentication_failed"
                },
                status_codes=[str(status.HTTP_401_UNAUTHORIZED)]
            ),
            OpenApiExample(
                'Permission Error',
                summary='Insufficient permissions',
                description='Response when user lacks required permissions',
                value={
                    "message": "You do not have permission to perform this action.",
                    "status": "error",
                    "code": "permission_denied"
                },
                status_codes=[str(status.HTTP_403_FORBIDDEN)]
            ),
            OpenApiExample(
                'Not Found Error',
                summary='Resource not found',
                description='Response when requested resource does not exist',
                value={
                    "message": "Not found.",
                    "status": "error",
                    "code": "not_found"
                },
                status_codes=[str(status.HTTP_404_NOT_FOUND)]
            )
        ]


# Common OpenAPI parameters for consistent documentation
class CommonParameters:
    """Common OpenAPI parameters used across multiple endpoints"""
    
    PAGINATION = [
        OpenApiParameter(
            name='page',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Page number for pagination',
            required=False
        ),
        OpenApiParameter(
            name='page_size',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Number of items per page (max 100)',
            required=False
        )
    ]
    
    SEARCH_FILTERS = [
        OpenApiParameter(
            name='search',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Search query string',
            required=False
        ),
        OpenApiParameter(
            name='ordering',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Order results by field (prefix with - for descending)',
            required=False
        )
    ]
    
    LOCATION_FILTERS = [
        OpenApiParameter(
            name='latitude',
            type=OpenApiTypes.FLOAT,
            location=OpenApiParameter.QUERY,
            description='Latitude for location-based queries',
            required=False
        ),
        OpenApiParameter(
            name='longitude',
            type=OpenApiTypes.FLOAT,
            location=OpenApiParameter.QUERY,
            description='Longitude for location-based queries',
            required=False
        ),
        OpenApiParameter(
            name='radius',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Search radius in kilometers',
            required=False
        )
    ]
    
    USER_FILTERS = [
        OpenApiParameter(
            name='age_min',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Minimum age filter',
            required=False
        ),
        OpenApiParameter(
            name='age_max',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Maximum age filter',
            required=False
        ),
        OpenApiParameter(
            name='gender',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Gender filter (male, female, other)',
            required=False
        ),
        OpenApiParameter(
            name='interests',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Comma-separated list of interest IDs',
            required=False
        )
    ]


# Common schema decorators for consistent documentation
def authentication_required_schema():
    """Schema decorator for endpoints requiring authentication"""
    return extend_schema(
        tags=['Authentication'],
        summary='Authentication Required',
        description='This endpoint requires valid JWT authentication. Include the access token in the Authorization header.',
        parameters=[
            OpenApiParameter(
                name='Authorization',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.HEADER,
                description='Bearer token for authentication',
                required=True
            )
        ]
    )


def paginated_list_schema(operation_id, summary, description):
    """Schema decorator for paginated list endpoints"""
    return extend_schema(
        operation_id=operation_id,
        summary=summary,
        description=description,
        tags=['Pagination'],
        parameters=CommonParameters.PAGINATION + CommonParameters.SEARCH_FILTERS
    )


def location_based_schema(operation_id, summary, description):
    """Schema decorator for location-based endpoints"""
    return extend_schema(
        operation_id=operation_id,
        summary=summary,
        description=description,
        tags=['Location Services'],
        parameters=CommonParameters.LOCATION_FILTERS
    )


def user_search_schema(operation_id, summary, description):
    """Schema decorator for user search endpoints"""
    return extend_schema(
        operation_id=operation_id,
        summary=summary,
        description=description,
        tags=['Matching & Discovery'],
        parameters=CommonParameters.USER_FILTERS + CommonParameters.LOCATION_FILTERS + CommonParameters.SEARCH_FILTERS
    )


def file_upload_schema(operation_id, summary, description, file_types=None):
    """Schema decorator for file upload endpoints"""
    if file_types is None:
        file_types = ['image/jpeg', 'image/png', 'video/mp4']
    
    return extend_schema(
        operation_id=operation_id,
        summary=summary,
        description=description,
        tags=['File Upload'],
        parameters=[
            OpenApiParameter(
                name='file',
                type=OpenApiTypes.BINARY,
                location=OpenApiParameter.QUERY,
                description=f'File to upload. Supported types: {", ".join(file_types)}',
                required=True
            )
        ]
    )


def payment_schema(operation_id, summary, description):
    """Schema decorator for payment-related endpoints"""
    return extend_schema(
        operation_id=operation_id,
        summary=summary,
        description=description,
        tags=['Monetization'],
        parameters=[
            OpenApiParameter(
                name='payment_method',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Payment method ID',
                required=True
            )
        ]
    )


def real_time_schema(operation_id, summary, description):
    """Schema decorator for real-time communication endpoints"""
    return extend_schema(
        operation_id=operation_id,
        summary=summary,
        description=description,
        tags=['Chat & Messaging'],
        parameters=[
            OpenApiParameter(
                name='participant_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='ID of the participant',
                required=True
            )
        ]
    )


# Custom schema examples for different data types
class SchemaExamples:
    """Common schema examples for different data types"""
    
    USER_EXAMPLE = {
        "id": 1,
        "email": "user@example.com",
        "name": "John Doe",
        "username": "john_doe",
        "age": 25,
        "gender": "male",
        "location": "New York, NY",
        "bio": "Love traveling and photography",
        "profile_picture": "https://example.com/profile.jpg",
        "is_verified": True,
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z"
    }
    
    CHAT_EXAMPLE = {
        "id": 1,
        "name": "John & Jane",
        "chat_type": "private",
        "participants": [1, 2],
        "last_message": {
            "content": "Hello! How are you?",
            "sender": 1,
            "timestamp": "2024-01-01T12:00:00Z"
        },
        "unread_count": 2,
        "created_at": "2024-01-01T10:00:00Z"
    }
    
    MESSAGE_EXAMPLE = {
        "id": 1,
        "content": "Hello! How are you?",
        "message_type": "text",
        "sender": 1,
        "chat": 1,
        "timestamp": "2024-01-01T12:00:00Z",
        "is_read": False,
        "media_url": None,
        "tip_amount": 0
    }
    
    POST_EXAMPLE = {
        "id": 1,
        "content": "Having a great day at the beach!",
        "author": 1,
        "media_urls": ["https://example.com/beach.jpg"],
        "location": "Miami Beach",
        "visibility": "public",
        "likes_count": 15,
        "comments_count": 3,
        "shares_count": 2,
        "created_at": "2024-01-01T14:00:00Z"
    }
    
    SUBSCRIPTION_EXAMPLE = {
        "id": 1,
        "plan": {
            "id": 1,
            "name": "Premium",
            "price_usd": 9.99,
            "duration_days": 30,
            "features": ["unlimited_likes", "see_who_liked_you", "boost_profile"]
        },
        "status": "active",
        "started_at": "2024-01-01T00:00:00Z",
        "expires_at": "2024-01-31T00:00:00Z"
    }
    
    GIFT_EXAMPLE = {
        "id": 1,
        "name": "Rose Bouquet",
        "description": "A beautiful bouquet of roses",
        "category": "romance",
        "price_bondcoins": 50,
        "image_url": "https://example.com/rose.jpg",
        "is_premium": False
    }
    
    LOCATION_EXAMPLE = {
        "id": 1,
        "latitude": 40.7128,
        "longitude": -74.0060,
        "accuracy": 10.5,
        "address": "New York, NY, USA",
        "city": "New York",
        "state": "NY",
        "country": "USA",
        "timestamp": "2024-01-01T12:00:00Z"
    }


# Custom response schemas
class ResponseSchemas:
    """Common response schemas for consistent documentation"""
    
    SUCCESS_RESPONSE = {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Success message"
            },
            "status": {
                "type": "string",
                "enum": ["success"],
                "description": "Response status"
            },
            "data": {
                "type": "object",
                "description": "Response data"
            }
        }
    }
    
    ERROR_RESPONSE = {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Error message"
            },
            "status": {
                "type": "string",
                "enum": ["error"],
                "description": "Response status"
            },
            "errors": {
                "type": "object",
                "description": "Field-specific error messages"
            },
            "code": {
                "type": "string",
                "description": "Error code"
            }
        }
    }
    
    PAGINATED_RESPONSE = {
        "type": "object",
        "properties": {
            "count": {
                "type": "integer",
                "description": "Total number of items"
            },
            "next": {
                "type": "string",
                "nullable": True,
                "description": "URL to next page"
            },
            "previous": {
                "type": "string",
                "nullable": True,
                "description": "URL to previous page"
            },
            "results": {
                "type": "array",
                "description": "Array of results"
            }
        }
    }


# Webhook schemas for payment processing
class WebhookSchemas:
    """Schemas for webhook endpoints"""
    
    PAYMENT_WEBHOOK = extend_schema(
        operation_id='payment_webhook',
        summary='Payment Webhook',
        description='Handle payment webhooks from external providers',
        tags=['Monetization'],
        parameters=[
            OpenApiParameter(
                name='provider',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='Payment provider (stripe, paypal, etc.)',
                required=True
            )
        ],
        examples=[
            OpenApiExample(
                'Stripe Webhook',
                summary='Stripe payment webhook payload',
                description='Example webhook payload from Stripe',
                value={
                    "id": "evt_1234567890",
                    "object": "event",
                    "type": "payment_intent.succeeded",
                    "data": {
                        "object": {
                            "id": "pi_1234567890",
                            "amount": 999,
                            "currency": "usd",
                            "status": "succeeded"
                        }
                    }
                }
            )
        ]
    )


# Custom schema generation for complex endpoints
def generate_chat_schema():
    """Generate comprehensive schema for chat endpoints"""
    return extend_schema(
        tags=['Chat & Messaging'],
        summary='Chat Management',
        description='Manage real-time chat conversations, messages, and calls',
        examples=[
            OpenApiExample(
                'Create Chat',
                summary='Create new chat conversation',
                description='Create a new chat conversation between users',
                value={
                    "participants": [1, 2, 3],
                    "chat_type": "group",
                    "name": "Friends Chat"
                }
            ),
            OpenApiExample(
                'Send Message',
                summary='Send a message in chat',
                description='Send a text, voice, or media message',
                value={
                    "content": "Hello! How are you?",
                    "message_type": "text",
                    "media_url": None,
                    "tip_amount": 0
                }
            )
        ]
    )


def generate_matching_schema():
    """Generate comprehensive schema for matching endpoints"""
    return extend_schema(
        tags=['Matching & Discovery'],
        summary='User Matching',
        description='Find and interact with potential matches based on preferences and location',
        parameters=[
            OpenApiParameter(
                name='algorithm',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Matching algorithm to use',
                enum=['location_based', 'interest_based', 'compatibility', 'hybrid']
            ),
            OpenApiParameter(
                name='max_distance',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Maximum distance for matches (km)',
                default=50
            )
        ],
        examples=[
            OpenApiExample(
                'User Search',
                summary='Search for users with filters',
                description='Search for users with various filters',
                value={
                    "age_min": 18,
                    "age_max": 35,
                    "gender": "female",
                    "distance": 25,
                    "interests": ["travel", "music", "photography"]
                }
            ),
            OpenApiExample(
                'User Interaction',
                summary='Like or dislike a user',
                description='Express interest in a user',
                value={
                    "target_user_id": 123,
                    "action": "like",
                    "interaction_type": "like"
                }
            )
        ]
    )
