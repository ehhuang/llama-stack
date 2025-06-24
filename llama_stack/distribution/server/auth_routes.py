# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from llama_stack.distribution.datatypes import GitHubAuthConfig
from llama_stack.log import get_logger

from .github_oauth_auth_provider import (
    GITHUB_CALLBACK_PATH,
    GITHUB_LOGIN_PATH,
    GitHubAuthProvider,
)

logger = get_logger(name=__name__, category="auth_routes")


def create_github_auth_router(config: GitHubAuthConfig) -> APIRouter:
    """Create and configure GitHub authentication router."""
    auth_provider = GitHubAuthProvider(config)
    router = APIRouter()
    oauth_states: dict[str, dict] = {}

    def cleanup_expired_states() -> None:
        """Remove expired OAuth states."""
        now = datetime.now(UTC)
        expired_states = [
            state
            for state, data in oauth_states.items()
            if (now - data["created_at"]).seconds > 300  # 5 minutes
        ]
        for state in expired_states:
            oauth_states.pop(state, None)

    @router.get(GITHUB_LOGIN_PATH)
    async def github_login(request: Request, redirect_url: str | None = None):
        """Initiate GitHub OAuth flow."""
        cleanup_expired_states()

        # Validate redirect URL if provided
        if redirect_url:
            if not auth_provider.config.allowed_redirect_urls:
                raise HTTPException(status_code=400, detail="Redirect URLs not configured")
            if redirect_url not in auth_provider.config.allowed_redirect_urls:
                raise HTTPException(status_code=400, detail="Invalid redirect URL")

        state = secrets.token_urlsafe(32)

        oauth_states[state] = {
            "created_at": datetime.now(UTC),
            "redirect_url": redirect_url,
        }

        # Get authorization URL
        auth_url = auth_provider.get_authorization_url(state, request)

        logger.debug(f"Redirecting to GitHub OAuth: {auth_url}")
        return RedirectResponse(url=auth_url)

    @router.get(GITHUB_CALLBACK_PATH)
    async def github_callback(code: str, state: str, request: Request):
        """Handle GitHub OAuth callback."""
        # Validate state parameter
        if state not in oauth_states:
            logger.warning(f"Invalid OAuth state received: {state}")
            raise HTTPException(status_code=400, detail="Invalid state parameter")

        state_data = oauth_states.pop(state)

        # Check state expiry
        if (datetime.now(UTC) - state_data["created_at"]).seconds > 300:
            logger.warning("OAuth state expired")
            raise HTTPException(status_code=400, detail="State expired")

        try:
            # Complete OAuth flow
            access_token = await auth_provider.complete_oauth_flow(code, request)

            logger.info("GitHub OAuth successful")

            redirect_url = state_data.get("redirect_url")
            if redirect_url:
                # Validate redirect URL from state
                if redirect_url not in auth_provider.config.allowed_redirect_urls:
                    raise HTTPException(status_code=400, detail="Invalid redirect URL in state")

                import urllib.parse

                params = urllib.parse.urlencode({"token": access_token})
                return RedirectResponse(url=f"{redirect_url}#{params}")
            else:
                # For API calls, only return the access token
                return JSONResponse(content={"access_token": access_token})

        except ValueError as e:
            logger.error(f"GitHub OAuth error: {e}")
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            logger.exception("Unexpected error during GitHub OAuth")
            raise HTTPException(status_code=500, detail="Authentication failed") from e

    return router
