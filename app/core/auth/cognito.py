from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from aws_jwt_verify import CognitoJwtVerifier
from aws_jwt_verify.exceptions import JwtValidationError
from pydantic import BaseModel

from app.core.config import settings

# Initialize security scheme
security = HTTPBearer()

# Initialize Cognito JWT verifier
cognito_verifier = CognitoJwtVerifier.create(
    user_pool_id=settings.COGNITO_USER_POOL_ID,
    client_id=settings.COGNITO_APP_CLIENT_ID,
    region=settings.AWS_REGION
)

class CognitoToken(BaseModel):
    """Model for Cognito token claims"""
    sub: str
    email: str
    cognito_groups: list[str] = []
    token_use: str
    scope: Optional[str] = None

async def get_current_user(
    auth: HTTPAuthorizationCredentials = Security(security)
) -> CognitoToken:
    """
    Validate the access token and return the current user.
    
    Args:
        auth: The authorization credentials containing the access token
        
    Returns:
        CognitoToken: The validated token claims
        
    Raises:
        HTTPException: If the token is invalid or expired
    """
    try:
        # Verify the JWT token
        claims = await cognito_verifier.verify(auth.credentials)
        
        # Convert claims to CognitoToken model
        token = CognitoToken(
            sub=claims["sub"],
            email=claims["email"],
            cognito_groups=claims.get("cognito:groups", []),
            token_use=claims["token_use"],
            scope=claims.get("scope")
        )
        
        return token
        
    except JwtValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )

def requires_scope(required_scope: str):
    """
    Decorator to check if the user has the required scope.
    
    Args:
        required_scope: The scope required to access the endpoint
    """
    async def scope_validation(user: CognitoToken = Security(get_current_user)):
        if not user.scope or required_scope not in user.scope.split():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required scope: {required_scope}"
            )
        return user
    return scope_validation

def requires_group(required_group: str):
    """
    Decorator to check if the user belongs to the required Cognito group.
    
    Args:
        required_group: The Cognito group required to access the endpoint
    """
    async def group_validation(user: CognitoToken = Security(get_current_user)):
        if required_group not in user.cognito_groups:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required group: {required_group}"
            )
        return user
    return group_validation 