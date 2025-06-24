# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import Request
from jose import jwt

from llama_stack.distribution.datatypes import GitHubAuthConfig, User
from llama_stack.log import get_logger

from .auth_providers import AuthProvider, get_attributes_from_claims

logger = get_logger(name=__name__, category="github_auth")

# GitHub API constants
GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_OAUTH_BASE_URL = "https://github.com"

# GitHub OAuth route paths
GITHUB_LOGIN_PATH = "/auth/github/login"
GITHUB_CALLBACK_PATH = "/auth/github/callback"


class GitHubAuthProvider(AuthProvider):
    """Authentication provider for GitHub OAuth flow and JWT validation."""

    def __init__(self, config: GitHubAuthConfig):
        self.config = config

    async def validate_token(self, token: str, scope: dict | None = None) -> User:
        """Validate a GitHub-issued JWT token."""
        try:
            claims = self.verify_jwt(token)

            principal = claims["sub"]
            attributes = get_attributes_from_claims(claims, self.config.claims_mapping)

            return User(principal=principal, attributes=attributes)

        except Exception as e:
            logger.exception("Error validating GitHub JWT")
            raise ValueError(f"Invalid GitHub JWT token: {str(e)}") from e

    async def close(self):
        """Clean up any resources."""
        pass

    def setup_routes(self, app):
        """Setup GitHub OAuth routes."""
        from .auth_routes import create_github_auth_router

        github_router = create_github_auth_router(self.config)
        app.include_router(github_router)

    def get_public_paths(self) -> list[str]:
        """GitHub OAuth paths that don't require authentication."""
        return ["/auth/github/"]

    def get_auth_error_message(self, scope: dict | None = None) -> str:
        """Return GitHub-specific authentication error message."""
        if scope:
            headers = dict(scope.get("headers", []))
            host = headers.get(b"host", b"").decode()
            scheme = scope.get("scheme", "http")

            if host:
                auth_url = f"{scheme}://{host}{GITHUB_LOGIN_PATH}"
                return f"Authentication required. Please authenticate via GitHub at {auth_url}"

        return f"Authentication required. Please authenticate by visiting {GITHUB_LOGIN_PATH} to start the authentication flow."

    # OAuth flow methods
    def get_authorization_url(self, state: str, request: Request) -> str:
        """Generate GitHub OAuth authorization URL."""
        params = {
            "client_id": self.config.github_client_id,
            "redirect_uri": _build_callback_url(request),
            "scope": "read:user read:org",
            "state": state,
        }
        return f"{GITHUB_OAUTH_BASE_URL}/login/oauth/authorize?" + urlencode(params)

    async def complete_oauth_flow(self, code: str, request: Request) -> str:
        """Complete the GitHub OAuth flow and return JWT access token."""
        # Exchange code for token
        logger.debug("Exchanging code for GitHub access token")
        token_data = await self._exchange_code_for_token(code, request)

        if "error" in token_data:
            raise ValueError(f"GitHub OAuth error: {token_data.get('error_description', token_data['error'])}")

        access_token = token_data["access_token"]

        # Get user info
        logger.debug("Fetching GitHub user info")
        github_info = await self._get_user_info(access_token)

        # Create JWT
        logger.debug(f"Creating JWT for user: {github_info['user']['login']}")
        jwt_token = self._create_jwt_token(github_info)

        return jwt_token

    def verify_jwt(self, token: str) -> Any:
        """Verify and decode a GitHub-issued JWT token."""
        try:
            payload = jwt.decode(
                token,
                self.config.jwt_secret,
                algorithms=[self.config.jwt_algorithm],
                audience=self.config.jwt_audience,
                issuer=self.config.jwt_issuer,
            )
            return payload
        except jwt.JWTError as e:
            raise ValueError(f"Invalid JWT token: {e}") from e

    # Private helper methods
    async def _exchange_code_for_token(self, code: str, request: Request) -> Any:
        """Exchange authorization code for GitHub access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GITHUB_OAUTH_BASE_URL}/login/oauth/access_token",
                json={
                    "client_id": self.config.github_client_id,
                    "client_secret": self.config.github_client_secret,
                    "code": code,
                    "redirect_uri": _build_callback_url(request),
                },
                headers={"Accept": "application/json"},
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()

    async def _get_user_info(self, access_token: str) -> dict:
        """Fetch user info and organizations from GitHub."""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github.v3+json",
        }

        async with httpx.AsyncClient() as client:
            # Fetch user and orgs in parallel
            user_task = client.get(f"{GITHUB_API_BASE_URL}/user", headers=headers, timeout=10.0)
            orgs_task = client.get(f"{GITHUB_API_BASE_URL}/user/orgs", headers=headers, timeout=10.0)

            user_response, orgs_response = await asyncio.gather(user_task, orgs_task)

            user_response.raise_for_status()
            orgs_response.raise_for_status()

            user_data = user_response.json()
            orgs_data = orgs_response.json()

            # Extract organization names
            organizations = [org["login"] for org in orgs_data]

            return {
                "user": user_data,
                "organizations": organizations,
            }

    def _create_jwt_token(self, github_info: dict) -> Any:
        """Create JWT token with GitHub user information."""
        user = github_info["user"]
        orgs = github_info["organizations"]
        teams = github_info.get("teams", [])

        # Create JWT claims that map to Llama Stack attributes
        now = datetime.now(UTC)
        claims = {
            "sub": user["login"],
            "aud": self.config.jwt_audience,
            "iss": self.config.jwt_issuer,
            "exp": now + timedelta(seconds=self.config.token_expiry),
            "iat": now,
            "nbf": now,
            # Custom claims that will be mapped by claims_mapping
            "github_username": user["login"],
            "github_user_id": str(user["id"]),
            "github_orgs": orgs,
            "github_teams": teams,
            "email": user.get("email"),
            "name": user.get("name"),
            "avatar_url": user.get("avatar_url"),
        }

        return jwt.encode(claims, self.config.jwt_secret, algorithm=self.config.jwt_algorithm)


def _build_callback_url(request: Request) -> str:
    """Build the GitHub OAuth callback URL from the current request."""
    callback_url = str(request.url_for("github_callback"))
    return callback_url
