# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt

from llama_stack.distribution.datatypes import GitHubAuthConfig
from llama_stack.distribution.server.auth import AuthenticationMiddleware
from llama_stack.distribution.server.auth_providers import get_attributes_from_claims
from llama_stack.distribution.server.auth_routes import create_github_auth_router
from llama_stack.distribution.server.github_oauth_auth_provider import GitHubAuthProvider


class MockResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self._json_data = json_data

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code != 200:
            raise Exception(f"HTTP error: {self.status_code}")


@pytest.fixture
def github_oauth_app():
    app = FastAPI()
    auth_config = {
        "type": "github_oauth",
        "github_client_id": "test_client_id",
        "github_client_secret": "test_client_secret",
        "jwt_secret": "test_jwt_secret",
        "jwt_algorithm": "HS256",
        "jwt_audience": "llama-stack",
        "jwt_issuer": "llama-stack-github",
        "token_expiry": 86400,
    }

    github_config = GitHubAuthConfig(**auth_config)

    # Add auth routes BEFORE middleware so they're not protected
    auth_router = create_github_auth_router(github_config)
    app.include_router(auth_router)

    # Then add auth middleware for other routes
    app.add_middleware(AuthenticationMiddleware, auth_config=github_config)

    @app.get("/test")
    def test_endpoint():
        return {"message": "Authentication successful"}

    return app


@pytest.fixture
def github_oauth_client(github_oauth_app):
    return TestClient(github_oauth_app)


def test_github_login_redirect(github_oauth_client):
    """Test that GitHub login endpoint returns redirect to GitHub"""
    response = github_oauth_client.get("/auth/github/login", follow_redirects=False)
    assert response.status_code == 307  # Temporary redirect
    assert "github.com/login/oauth/authorize" in response.headers["location"]
    assert "client_id=test_client_id" in response.headers["location"]
    assert "state=" in response.headers["location"]


async def mock_github_token_exchange_success(*args, **kwargs):
    """Mock successful GitHub token exchange"""
    return MockResponse(
        200,
        {
            "access_token": "github_access_token_123",
            "token_type": "bearer",
            "scope": "read:user,read:org",
        },
    )


class MockAsyncClient:
    """Mock httpx.AsyncClient for testing"""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def post(self, url, **kwargs):
        if "login/oauth/access_token" in url:
            return await mock_github_token_exchange_success()
        return MockResponse(404, {})

    async def get(self, url, **kwargs):
        if url.endswith("/user"):
            return MockResponse(
                200,
                {
                    "login": "test-user",
                    "id": 12345,
                    "email": "test@example.com",
                    "name": "Test User",
                    "avatar_url": "https://avatars.githubusercontent.com/u/12345",
                },
            )
        elif url.endswith("/user/orgs"):
            return MockResponse(
                200,
                [
                    {"login": "test-org-1"},
                    {"login": "test-org-2"},
                ],
            )
        return MockResponse(404, {})


@patch("httpx.AsyncClient", MockAsyncClient)
def test_github_callback_success(github_oauth_app):
    """Test successful GitHub OAuth callback"""
    # Get a fresh client for this test
    client = TestClient(github_oauth_app)

    # First, make a login request to generate a state
    login_response = client.get("/auth/github/login", follow_redirects=False)
    assert login_response.status_code == 307

    # Extract the state from the redirect URL
    location = login_response.headers["location"]
    import re

    state_match = re.search(r"state=([^&]+)", location)
    assert state_match
    state = state_match.group(1)

    # Now use that state in the callback
    response = client.get(f"/auth/github/callback?code=test_code&state={state}")

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    # Verify the JWT token contains the expected claims
    token = data["access_token"]
    # Decode without verification since this is a test
    claims = jwt.decode(token, "test_jwt_secret", algorithms=["HS256"], audience="llama-stack")
    assert claims["github_username"] == "test-user"
    assert claims["email"] == "test@example.com"


def test_github_callback_invalid_state(github_oauth_client):
    """Test GitHub callback with invalid state"""
    response = github_oauth_client.get("/auth/github/callback?code=test_code&state=invalid_state")
    assert response.status_code == 400
    assert "Invalid state parameter" in response.json()["detail"]


async def mock_github_token_exchange_error(*args, **kwargs):
    """Mock GitHub token exchange error"""
    return MockResponse(
        200, {"error": "bad_verification_code", "error_description": "The code passed is incorrect or expired."}
    )


class MockAsyncClientError:
    """Mock httpx.AsyncClient that returns error for token exchange"""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def post(self, url, **kwargs):
        if "login/oauth/access_token" in url:
            return await mock_github_token_exchange_error()
        return MockResponse(404, {})

    async def get(self, url, **kwargs):
        return MockResponse(404, {})


@patch("httpx.AsyncClient", MockAsyncClientError)
def test_github_callback_token_exchange_error(github_oauth_app):
    """Test GitHub callback with token exchange error"""
    client = TestClient(github_oauth_app)

    # First, make a login request to generate a state
    login_response = client.get("/auth/github/login", follow_redirects=False)
    assert login_response.status_code == 307

    # Extract the state from the redirect URL
    location = login_response.headers["location"]
    import re

    state_match = re.search(r"state=([^&]+)", location)
    assert state_match
    state = state_match.group(1)

    # Now use that state in the callback with bad code
    response = client.get(f"/auth/github/callback?code=bad_code&state={state}")
    assert response.status_code == 400
    assert "The code passed is incorrect or expired" in response.json()["detail"]


@pytest.fixture
def github_jwt_token():
    """Create a valid GitHub JWT token for testing"""
    claims = {
        "sub": "test-user",
        "aud": "llama-stack",
        "iss": "llama-stack-github",
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "iat": datetime.now(UTC),
        "nbf": datetime.now(UTC),
        "github_username": "test-user",
        "github_user_id": "12345",
        "github_orgs": ["test-org-1", "test-org-2"],
        "email": "test@example.com",
        "name": "Test User",
    }

    return jwt.encode(claims, "test_jwt_secret", algorithm="HS256")


def test_github_jwt_authentication_success(github_oauth_client, github_jwt_token):
    """Test API authentication with GitHub-issued JWT"""
    response = github_oauth_client.get("/test", headers={"Authorization": f"Bearer {github_jwt_token}"})
    assert response.status_code == 200
    assert response.json() == {"message": "Authentication successful"}


def test_github_jwt_authentication_invalid_token(github_oauth_client):
    """Test API authentication with invalid JWT"""
    response = github_oauth_client.get("/test", headers={"Authorization": "Bearer invalid.jwt.token"})
    assert response.status_code == 401
    assert "Invalid GitHub JWT token" in response.json()["error"]["message"]


def test_github_jwt_authentication_expired_token(github_oauth_client):
    """Test API authentication with expired JWT"""
    # Create an expired token
    claims = {
        "sub": "test-user",
        "aud": "llama-stack",
        "iss": "llama-stack-github",
        "exp": datetime.now(UTC) - timedelta(hours=1),  # Expired
        "iat": datetime.now(UTC) - timedelta(hours=2),
        "nbf": datetime.now(UTC) - timedelta(hours=2),
        "github_username": "test-user",
    }

    expired_token = jwt.encode(claims, "test_jwt_secret", algorithm="HS256")

    response = github_oauth_client.get("/test", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401
    assert "Invalid GitHub JWT token" in response.json()["error"]["message"]


def test_github_jwt_authentication_wrong_audience(github_oauth_client):
    """Test API authentication with JWT having wrong audience"""
    claims = {
        "sub": "test-user",
        "aud": "wrong-audience",  # Wrong audience
        "iss": "llama-stack-github",
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "iat": datetime.now(UTC),
        "nbf": datetime.now(UTC),
        "github_username": "test-user",
    }

    wrong_audience_token = jwt.encode(claims, "test_jwt_secret", algorithm="HS256")

    response = github_oauth_client.get("/test", headers={"Authorization": f"Bearer {wrong_audience_token}"})
    assert response.status_code == 401
    assert "Invalid GitHub JWT token" in response.json()["error"]["message"]


def test_github_claims_mapping():
    """Test GitHub claims are properly mapped to attributes"""
    config = GitHubAuthConfig(
        type="github_oauth",
        github_client_id="test",
        github_client_secret="test",
        jwt_secret="test",
    )

    claims = {
        "sub": "test-user",
        "github_username": "test-user",
        "github_orgs": ["org1", "org2"],
        "github_teams": ["team1", "team2"],
        "github_user_id": "12345",
    }

    # Default mapping only maps "sub" to "roles"
    attributes = get_attributes_from_claims(claims, config.claims_mapping)

    assert "test-user" in attributes["roles"]
    # No other mappings by default
    assert len(attributes) == 1


@pytest.mark.asyncio
async def test_github_auth_provider_validate_token():
    """Test GitHubAuthProvider token validation"""
    config = GitHubAuthConfig(
        type="github_oauth",
        github_client_id="test",
        github_client_secret="test",
        jwt_secret="test_secret",
        jwt_algorithm="HS256",
        jwt_audience="test-audience",
        jwt_issuer="test-issuer",
    )

    provider = GitHubAuthProvider(config)

    # Create a valid token
    claims = {
        "sub": "test-user",
        "aud": "test-audience",
        "iss": "test-issuer",
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "iat": datetime.now(UTC),
        "nbf": datetime.now(UTC),
        "github_username": "test-user",
        "github_orgs": ["org1"],
        "github_user_id": "12345",
    }

    token = jwt.encode(claims, "test_secret", algorithm="HS256")

    user = await provider.validate_token(token)
    assert user.principal == "test-user"
    # Default mapping only maps "sub" to "roles"
    assert "test-user" in user.attributes["roles"]
    # No other mappings by default
    assert len(user.attributes) == 1


@pytest.mark.asyncio
async def test_github_auth_provider_custom_claims_mapping():
    """Test GitHubAuthProvider with custom claims mapping"""
    config = GitHubAuthConfig(
        type="github_oauth",
        github_client_id="test",
        github_client_secret="test",
        jwt_secret="test_secret",
        jwt_algorithm="HS256",
        jwt_audience="test-audience",
        jwt_issuer="test-issuer",
        claims_mapping={
            "sub": "roles",
            "github_orgs": "teams",
            "github_teams": "teams",
            "github_user_id": "namespaces",
        },
    )

    provider = GitHubAuthProvider(config)

    # Create a valid token
    claims = {
        "sub": "test-user",
        "aud": "test-audience",
        "iss": "test-issuer",
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "iat": datetime.now(UTC),
        "nbf": datetime.now(UTC),
        "github_username": "test-user",
        "github_orgs": ["org1", "org2"],
        "github_teams": ["team1", "team2"],
        "github_user_id": "12345",
    }

    token = jwt.encode(claims, "test_secret", algorithm="HS256")

    user = await provider.validate_token(token)
    assert user.principal == "test-user"
    assert "test-user" in user.attributes["roles"]
    assert set(user.attributes["teams"]) == {"org1", "org2", "team1", "team2"}
    assert "12345" in user.attributes["namespaces"]


@pytest.mark.asyncio
async def test_github_auth_provider_invalid_token():
    """Test GitHubAuthProvider with invalid token"""
    config = GitHubAuthConfig(
        type="github_oauth",
        github_client_id="test",
        github_client_secret="test",
        jwt_secret="test_secret",
    )

    provider = GitHubAuthProvider(config)

    with pytest.raises(ValueError, match="Invalid GitHub JWT token"):
        await provider.validate_token("invalid.token.here")


def test_github_auth_provider_authorization_url():
    """Test GitHubAuthProvider generates correct authorization URL"""
    from unittest.mock import Mock

    config = GitHubAuthConfig(
        type="github_oauth",
        github_client_id="test_client_id",
        github_client_secret="test_secret",
        jwt_secret="test",
    )

    provider = GitHubAuthProvider(config)

    # Mock request object
    mock_request = Mock()
    mock_request.url_for.return_value = "http://localhost:8321/auth/github/callback"

    url = provider.get_authorization_url("test_state_123", mock_request)

    assert "https://github.com/login/oauth/authorize" in url
    assert "client_id=test_client_id" in url
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A8321%2Fauth%2Fgithub%2Fcallback" in url
    assert "state=test_state_123" in url
    assert "scope=read%3Auser+read%3Aorg" in url


@pytest.mark.asyncio
async def test_github_auth_provider_complete_flow():
    """Test complete OAuth flow in GitHubAuthProvider"""
    from unittest.mock import Mock

    config = GitHubAuthConfig(
        type="github_oauth",
        github_client_id="test_client_id",
        github_client_secret="test_secret",
        jwt_secret="test_jwt_secret",
        jwt_algorithm="HS256",
        jwt_audience="llama-stack",
        jwt_issuer="llama-stack-github",
    )

    provider = GitHubAuthProvider(config)

    # Mock request object
    mock_request = Mock()
    mock_request.url_for.return_value = "/auth/github/callback"
    mock_request.url.scheme = "http"
    mock_request.url.netloc = "localhost:8321"

    with patch("httpx.AsyncClient", MockAsyncClient):
        # Now returns just the JWT token
        token = await provider.complete_oauth_flow("test_code", mock_request)

    # Verify it's a JWT token by decoding it
    claims = jwt.decode(token, "test_jwt_secret", algorithms=["HS256"], audience="llama-stack")
    assert claims["github_username"] == "test-user"
    assert claims["github_orgs"] == ["test-org-1", "test-org-2"]
    assert claims["sub"] == "test-user"
