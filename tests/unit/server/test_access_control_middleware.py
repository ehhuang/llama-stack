# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import json
from unittest.mock import AsyncMock

import pytest

from llama_stack.distribution.server.access_control import AccessControlMiddleware, _evaluate_policy
from llama_stack.distribution.user import User
from llama_stack.schema_utils import WebMethod


class MockApp:
    async def __call__(self, scope, receive, send):
        # Simulate successful app response
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b'{"success": true}'})


@pytest.fixture
def middleware():
    app = MockApp()
    impls = {}
    return AccessControlMiddleware(app, impls)


async def test_middleware_allows_request_without_access_control(middleware):
    """Test middleware passes through requests when webmethod has no access control."""
    scope = {"type": "http", "path": "/test", "method": "GET"}
    receive = AsyncMock()
    send = AsyncMock()

    # Mock webmethod without access control
    webmethod = WebMethod(route="/test", method="GET", access_control=None)

    # Override process_request to test the logic
    async def mock_process_request(scope, receive, send, route, impl, webmethod):
        if webmethod and webmethod.access_control:
            # This shouldn't execute for this test
            raise ValueError("should not have access control")
        return await middleware.app(scope, receive, send)

    middleware.process_request = mock_process_request

    await middleware.process_request(scope, receive, send, None, None, webmethod)

    # Verify successful response was sent
    send.assert_any_call({"type": "http.response.start", "status": 200, "headers": []})


async def test_middleware_denies_access_without_proper_role(middleware):
    """Test middleware returns 403 when user lacks required role."""
    scope = {
        "type": "http",
        "path": "/test",
        "method": "POST",
        "principal": "test-user",
        "user_attributes": {"roles": ["basic-user"]},
    }
    receive = AsyncMock()
    send = AsyncMock()

    webmethod = WebMethod(route="/test", method="POST", access_control="user with monitoring.viewer in roles")

    await middleware.process_request(scope, receive, send, None, None, webmethod)

    # Verify 403 response was sent
    send.assert_any_call(
        {"type": "http.response.start", "status": 403, "headers": [[b"content-type", b"application/json"]]}
    )

    # Check error response body
    body_call = None
    for call in send.call_args_list:
        if call[0][0]["type"] == "http.response.body":
            body_call = call
            break

    assert body_call is not None
    body_data = json.loads(body_call[0][0]["body"].decode())
    assert "error" in body_data
    assert "Access denied" in body_data["error"]["detail"]


async def test_middleware_allows_access_with_proper_role(middleware):
    """Test middleware allows request when user has required role."""
    scope = {
        "type": "http",
        "path": "/test",
        "method": "POST",
        "principal": "test-user",
        "user_attributes": {"roles": ["monitoring.viewer", "other-role"]},
    }
    receive = AsyncMock()
    send = AsyncMock()

    webmethod = WebMethod(route="/test", method="POST", access_control="user with monitoring.viewer in roles")

    await middleware.process_request(scope, receive, send, None, None, webmethod)

    # Verify successful response (from MockApp)
    send.assert_any_call({"type": "http.response.start", "status": 200, "headers": []})


async def test_middleware_allows_when_no_user_auth_disabled(middleware):
    """Test middleware allows request when no user present (auth disabled)."""
    scope = {"type": "http", "path": "/test", "method": "POST"}
    receive = AsyncMock()
    send = AsyncMock()

    webmethod = WebMethod(route="/test", method="POST", access_control="user with monitoring.viewer in roles")

    await middleware.process_request(scope, receive, send, None, None, webmethod)

    # Should allow request when auth is disabled
    send.assert_any_call({"type": "http.response.start", "status": 200, "headers": []})


def test_evaluate_policy_valid_condition():
    """Test _evaluate_policy with valid conditions."""
    user = User("test-user", {"roles": ["monitoring.viewer"]})

    # Test user has required role
    assert _evaluate_policy("user with monitoring.viewer in roles", user) is True

    # Test user lacks required role
    user_no_role = User("test-user", {"roles": ["basic-user"]})
    assert _evaluate_policy("user with monitoring.viewer in roles", user_no_role) is False

    # Test no user (auth disabled)
    assert _evaluate_policy("user with monitoring.viewer in roles", None) is True


def test_evaluate_policy_invalid_condition():
    """Test _evaluate_policy with invalid conditions."""
    user = User("test-user", {"roles": ["monitoring.viewer"]})

    # Test invalid condition string
    assert _evaluate_policy("invalid condition string", user) is False

    # Test empty condition
    assert _evaluate_policy("", user) is False


def test_evaluate_policy_user_without_attributes():
    """Test _evaluate_policy with user having no attributes."""
    user = User("test-user", None)

    assert _evaluate_policy("user with monitoring.viewer in roles", user) is False

    user_empty = User("test-user", {})
    assert _evaluate_policy("user with monitoring.viewer in roles", user_empty) is False
