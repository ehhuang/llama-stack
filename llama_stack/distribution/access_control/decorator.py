# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import inspect
from collections.abc import Callable
from functools import wraps
from typing import TypeVar

from llama_stack.distribution.access_control.access_control import AccessDeniedError
from llama_stack.distribution.access_control.conditions import (
    UserWithValueInList,
    UserWithValueNotInList,
    parse_condition,
)
from llama_stack.distribution.request_headers import get_authenticated_user

T = TypeVar("T", bound=Callable)


def requires_access(policy: str) -> Callable[[T], T]:
    """Decorator that enforces access control on route functions.

    Supports two condition formats since there are no owners associated with APIs:
    - "user with VALUE in ATTRIBUTE" - user has specific value in attribute
    - "user with VALUE not in ATTRIBUTE" - user does NOT have specific value in attribute

    Args:
        policy: Access control policy string
    """

    def decorator(func: T) -> T:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            user = get_authenticated_user()

            if not _evaluate_policy(policy, user):
                raise AccessDeniedError("access-denied", None, user)
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            user = get_authenticated_user()

            if not _evaluate_policy(policy, user):
                raise AccessDeniedError("access-denied", None, user)

            return func(*args, **kwargs)

        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore

    return decorator


def _evaluate_policy(condition: str, user) -> bool:
    if not user:
        return False

    try:
        condition_obj = parse_condition(condition)

        if not (isinstance(condition_obj, UserWithValueInList) or isinstance(condition_obj, UserWithValueNotInList)):
            # Only support these two conditions
            return False

        # Create a dummy resource since we don't have one in this context
        class DummyResource:
            type = "api"
            identifier = "unknown"
            owner = user

        dummy_resource = DummyResource()

        return condition_obj.matches(dummy_resource, user)
    except (ValueError, AttributeError):
        return False
