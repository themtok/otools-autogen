from functools import wraps
import logging


def only_direct(func):
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


logger = logging.getLogger("otools_autogen")
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)