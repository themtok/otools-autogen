from functools import wraps
import logging
from datetime import datetime
import os


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
logger.setLevel(logging.ERROR)


timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_filename = f"logs/otools_autogen_llm_{timestamp}.log"

os.makedirs(os.path.dirname(log_filename), exist_ok=True)



llm_logger = logging.getLogger("otools_autogen_llm")
llm_logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(log_filename,encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

llm_logger.addHandler(file_handler)
# llm_logger.addHandler(console_handler)