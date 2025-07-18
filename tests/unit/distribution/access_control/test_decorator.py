# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

from unittest.mock import Mock, patch

import pytest

from llama_stack.distribution.access_control.access_control import AccessDeniedError
from llama_stack.distribution.access_control.decorator import (
    _evaluate_policy,
    requires_access,
)
from llama_stack.distribution.user import User


class TestPolicyConditionEvaluation:
    """Test suite for policy condition evaluation functionality."""

    def test_all_supported_condition_formats(self):
        """Test all supported condition formats in one comprehensive test."""
        # Test user with typical attributes
        user = Mock(spec=User)
        user.principal = "test-user"
        user.attributes = {"roles": ["admin", "user"], "teams": ["ml-team", "data-team"], "projects": ["llama-stack"]}

        # Test supported condition formats (only UserWithValueInList and UserWithValueNotInList)
        test_cases = [
            # Format: (condition, expected_result, description)
            ("user with admin in roles", True, "user has admin role"),
            ("user with viewer in roles", False, "user doesn't have viewer role"),
            ("user with ml-team in teams", True, "user is in ml-team"),
            ("user with other-team in teams", False, "user is not in other-team"),
            ("user with admin not in roles", False, "user DOES have admin role (negative)"),
            ("user with viewer not in roles", True, "user does NOT have viewer role (negative)"),
            # These conditions are not supported by the current implementation
            ("user is owner", False, "user is owner condition not supported"),
            ("user is not owner", False, "user is not owner condition not supported"),
            ("user in owners roles", False, "user in owners condition not supported"),
            ("user not in owners roles", False, "user not in owners condition not supported"),
        ]

        for condition, expected, description in test_cases:
            result = _evaluate_policy(condition, user)
            assert result == expected, f"Failed: {condition} - {description}"

        print("✅ All supported condition formats tested successfully!")

    def test_policy_condition_evaluation(self):
        """Test the policy condition evaluation function."""
        user = Mock(spec=User)
        user.principal = "test-user"
        user.attributes = {"roles": ["monitoring.viewer", "user"], "teams": ["ml-team"]}

        # Test valid conditions
        assert _evaluate_policy("user with monitoring.viewer in roles", user)
        assert _evaluate_policy("user with ml-team in teams", user)

        # Test invalid conditions
        assert not _evaluate_policy("user with admin in roles", user)
        assert not _evaluate_policy("user with other-team in teams", user)

        # Test edge cases
        assert not _evaluate_policy("invalid condition", user)

    def test_policy_condition_evaluation_string_roles(self):
        """Test policy condition evaluation with string roles."""
        user = Mock(spec=User)
        user.principal = "test-user"
        user.attributes = {"roles": "monitoring.viewer"}  # Single string instead of list

        # Should still work with string roles
        assert _evaluate_policy("user with monitoring.viewer in roles", user)

    def test_policy_condition_evaluation_no_attributes(self):
        """Test policy condition evaluation when user has no attributes."""
        user = Mock(spec=User)
        user.principal = "test-user"
        user.attributes = None

        # Should return False when user has no attributes
        assert not _evaluate_policy("user with monitoring.viewer in roles", user)

    def test_policy_condition_evaluation_missing_attribute(self):
        """Test policy condition evaluation when user lacks the required attribute."""
        user = Mock(spec=User)
        user.principal = "test-user"
        user.attributes = {"roles": ["user"]}  # Has roles but not teams

        # Should return False when user lacks the required attribute
        assert not _evaluate_policy("user with ml-team in teams", user)

    def test_user_is_owner_condition(self):
        """Test 'user is owner' condition."""
        user = Mock(spec=User)
        user.principal = "test-user"
        user.attributes = {"roles": ["user"]}

        # Should return False for "user is owner" condition (not supported)
        assert not _evaluate_policy("user is owner", user)

    def test_user_is_not_owner_condition(self):
        """Test 'user is not owner' condition."""
        user = Mock(spec=User)
        user.principal = "test-user"
        user.attributes = {"roles": ["user"]}

        # Should return False for "user is not owner" condition (not supported)
        assert not _evaluate_policy("user is not owner", user)

    def test_user_with_value_not_in_attribute(self):
        """Test 'user with value not in attribute' condition."""
        user = Mock(spec=User)
        user.principal = "test-user"
        user.attributes = {"roles": ["user", "viewer"]}

        # Should return True when user does NOT have the specified value
        assert _evaluate_policy("user with admin not in roles", user)

        # Should return False when user DOES have the specified value
        assert not _evaluate_policy("user with user not in roles", user)

    def test_user_in_owners_attribute(self):
        """Test 'user in owners attribute' condition."""
        user = Mock(spec=User)
        user.principal = "test-user"
        user.attributes = {"teams": ["ml-team", "data-team"]}

        # Should return False for "user in owners" condition (not supported)
        assert not _evaluate_policy("user in owners teams", user)

    def test_user_not_in_owners_attribute(self):
        """Test 'user not in owners attribute' condition."""
        user = Mock(spec=User)
        user.principal = "test-user"
        user.attributes = {"teams": ["ml-team", "data-team"]}

        # Should return False for "user not in owners" condition (not supported)
        assert not _evaluate_policy("user not in owners teams", user)

    def test_multiple_condition_formats(self):
        """Test various condition formats to ensure broad compatibility."""
        user = Mock(spec=User)
        user.principal = "admin-user"
        user.attributes = {"roles": ["admin", "user"], "teams": ["ml-team"], "projects": ["llama-stack"]}

        # Test different attribute types
        assert _evaluate_policy("user with admin in roles", user)
        assert _evaluate_policy("user with ml-team in teams", user)
        assert _evaluate_policy("user with llama-stack in projects", user)

        # Test negative cases
        assert not _evaluate_policy("user with viewer in roles", user)
        assert not _evaluate_policy("user with other-team in teams", user)

    def test_invalid_condition_format(self):
        """Test that invalid condition formats are handled gracefully."""
        user = Mock(spec=User)
        user.principal = "test-user"
        user.attributes = {"roles": ["user"]}

        # Should return False for invalid condition formats
        assert not _evaluate_policy("invalid condition format", user)
        assert not _evaluate_policy("user has admin", user)
        assert not _evaluate_policy("", user)


class TestRequiresAccessDecorator:
    """Test suite for @requires_access decorator functionality."""

    @patch("llama_stack.distribution.access_control.decorator.get_authenticated_user")
    def test_requires_access_decorator_allows_access(self, mock_get_user):
        """Test that decorator allows access when user has required role."""
        user = Mock(spec=User)
        user.principal = "test-user"
        user.attributes = {"roles": ["monitoring.viewer"]}
        mock_get_user.return_value = user

        @requires_access("user with monitoring.viewer in roles")
        async def test_func():
            return "success"

        # Should complete without raising exception
        import asyncio

        result = asyncio.run(test_func())
        assert result == "success"

    @patch("llama_stack.distribution.access_control.decorator.get_authenticated_user")
    def test_requires_access_decorator_denies_access(self, mock_get_user):
        """Test that decorator denies access when user lacks required role."""
        user = Mock(spec=User)
        user.principal = "test-user"
        user.attributes = {"roles": ["user"]}
        mock_get_user.return_value = user

        @requires_access("user with monitoring.viewer in roles")
        async def test_func():
            return "success"

        # Should raise AccessDeniedError
        import asyncio

        with pytest.raises(AccessDeniedError):
            asyncio.run(test_func())

    @patch("llama_stack.distribution.access_control.decorator.get_authenticated_user")
    def test_requires_access_decorator_no_user(self, mock_get_user):
        """Test that decorator denies access when no user is authenticated."""
        mock_get_user.return_value = None

        @requires_access("user with monitoring.viewer in roles")
        async def test_func():
            return "success"

        # Should raise AccessDeniedError
        import asyncio

        with pytest.raises(AccessDeniedError):
            asyncio.run(test_func())

    def test_requires_access_decorator_sync_function(self):
        """Test that decorator works with synchronous functions."""

        @requires_access("user with monitoring.viewer in roles")
        def sync_func():
            return "success"

        # Function should be decorated (this just tests it doesn't crash)
        assert callable(sync_func)

    @patch("llama_stack.distribution.access_control.decorator.get_authenticated_user")
    def test_requires_access_with_different_condition_types(self, mock_get_user):
        """Test that decorator works with various condition types."""
        user = Mock(spec=User)
        user.principal = "admin-user"
        user.attributes = {"roles": ["admin", "user"], "teams": ["ml-team"], "projects": ["llama-stack"]}
        mock_get_user.return_value = user

        # Test with different condition formats
        @requires_access("user with admin in roles")
        async def test_admin_func():
            return "admin-success"

        @requires_access("user with ml-team in teams")
        async def test_team_func():
            return "team-success"

        # Only test supported conditions
        import asyncio

        assert asyncio.run(test_admin_func()) == "admin-success"
        assert asyncio.run(test_team_func()) == "team-success"

    @patch("llama_stack.distribution.access_control.decorator.get_authenticated_user")
    def test_requires_access_with_negative_conditions(self, mock_get_user):
        """Test that decorator works with negative condition types."""
        user = Mock(spec=User)
        user.principal = "regular-user"
        user.attributes = {"roles": ["user"]}
        mock_get_user.return_value = user

        @requires_access("user with admin not in roles")
        async def test_not_admin_func():
            return "not-admin-success"

        # Should succeed because user does NOT have admin role
        import asyncio

        result = asyncio.run(test_not_admin_func())
        assert result == "not-admin-success"

    @patch("llama_stack.distribution.access_control.decorator.get_authenticated_user")
    def test_requires_access_with_invalid_condition(self, mock_get_user):
        """Test that decorator denies access for invalid conditions."""
        user = Mock(spec=User)
        user.principal = "test-user"
        user.attributes = {"roles": ["user"]}
        mock_get_user.return_value = user

        @requires_access("invalid condition format")
        async def test_invalid_func():
            return "should-not-reach"

        # Should raise AccessDeniedError for invalid condition
        import asyncio

        with pytest.raises(AccessDeniedError):
            asyncio.run(test_invalid_func())
