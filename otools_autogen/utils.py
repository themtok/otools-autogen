from functools import wraps
import logging
from datetime import datetime
import os


def only_direct(func):
    """
    A decorator that ensures the decorated asynchronous function is only executed 
    if the `ctx` argument is either not provided or does not have a `topic_id` attribute.

    If `ctx` is provided and has a `topic_id` attribute, the function will return `None` 
    instead of executing the decorated function.

    Args:
        func (Callable): The asynchronous function to be decorated.

    Returns:
        Callable: The wrapped asynchronous function.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        ctx = kwargs.get("ctx", None)
        if ctx is None and len(args) >= 3:
            ctx = args[2]
        if ctx is None or ctx.topic_id is None:
            return await func(*args, **kwargs)
        else:
            return None
    return wrapper