"""Error response schemas for OpenAPI documentation."""

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Standard error response."""

    detail: str = Field(..., description="Error message describing what went wrong")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"detail": "Resource not found"},
                {"detail": "Invalid request"},
            ]
        }
    }


class ValidationErrorDetail(BaseModel):
    """Validation error response (422)."""

    detail: list[dict] = Field(
        ...,
        description="List of validation errors with location, message, and type",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "detail": [
                        {
                            "loc": ["body", "email"],
                            "msg": "invalid email format",
                            "type": "value_error.email",
                        }
                    ]
                }
            ]
        }
    }


class AuthErrorDetail(BaseModel):
    """Authentication error response (401)."""

    detail: str = Field(..., description="Authentication error message")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"detail": "Invalid or expired token"},
                {"detail": "Missing bearer token"},
                {"detail": "Incorrect email or password"},
            ]
        }
    }


# Common error response configurations for FastAPI endpoints
COMMON_RESPONSES = {
    401: {
        "model": AuthErrorDetail,
        "description": "Authentication failed - Invalid or missing token",
    },
    422: {
        "model": ValidationErrorDetail,
        "description": "Validation error - Request body does not match expected schema",
    },
}

# Ownership-protected endpoints responses
OWNERSHIP_RESPONSES = {
    **COMMON_RESPONSES,
    403: {
        "model": ErrorDetail,
        "description": "Forbidden - User is not the owner of this resource",
    },
    404: {
        "model": ErrorDetail,
        "description": "Not found - Resource does not exist",
    },
}
