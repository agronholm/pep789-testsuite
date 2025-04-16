from __future__ import annotations

import inspect
import sys
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from types import CodeType, FrameType

__version__ = "1.0.0"

@dataclass(frozen=True, slots=True)
class YieldPrevented:
    frame: FrameType | None
    reason: str | None
    allowed: bool

yields_prevented = ContextVar[YieldPrevented]("yields_prevented", default=False)


def check_yield(code: CodeType, instruction_offset: int, retval: object):
    # if code.co_flags & inspect.CO_ASYNC_GENERATOR and retval.__class__.__name__ == "async_generator_wrapped_value":
    #     frame = sys._getframe(1)
    #     print(f"yielded at {frame.f_code.co_filename}:{frame.f_lineno} in {frame.f_code.co_name}()")
    #     print(f"yielded {retval!r} in {code.co_name} at offset {instruction_offset}")
    # https://github.com/python/cpython/issues/129013
    # if prevent := yields_prevented.get() and code.co_flags & (inspect.CO_ASYNC_GENERATOR | inspect.CO_GENERATOR):
    #     print(f"checking yield; {retval=}")
    if code.co_flags & inspect.CO_GENERATOR:
        if prevent := yields_prevented.get():
            print(f"checking yield; {retval=}")
    if (
        retval is not None
        and (prevent := yields_prevented.get())
    ):
        if prevent.allowed:
            return

        if (
            code.co_flags & inspect.CO_ASYNC_GENERATOR
            and retval.__class__.__name__ == "async_generator_wrapped_value"
        ):
            if prevent.frame == sys._getframe(1):
                print(
                    f"yield prevented in {code.co_name} at offset {instruction_offset}; retval: {retval!r}"
                )
                raise RuntimeError(prevent.reason)
        elif code.co_flags & inspect.CO_GENERATOR:
            print(f"hit a generator check {prevent.frame=}  {sys._getframe(1)=}")
            if prevent.frame == sys._getframe(1):
                print(
                    f"yield prevented in {code.co_name} at offset {instruction_offset}; retval: {retval!r}"
                )
                raise RuntimeError(prevent.reason)



# def check_return(code: CodeType, instruction_offset: int, retval: object):
#     assert code.co_flags is not None
#     assert inspect.CO_ASYNC_GENERATOR is not None
#     if code.co_flags & inspect.CO_ASYNC_GENERATOR and (reason := yields_prevented.get()):
#         print("returning from", code.co_name, "at offset", instruction_offset, "with retval", retval)


@contextmanager
def set_yields_prevented(reason: str | None, *, stacklevel: int = 1):
    frame = sys._getframe(stacklevel + 1)
    location = f"{frame.f_code.co_filename}:{frame.f_lineno}"

    if reason is None:
        old_value = yields_prevented.get(None)
        if old_value is None:
            prevent = YieldPrevented(None, None, True)
        else:
            prevent = YieldPrevented(None, old_value.reason, True)
            print(f"yields allowed again in {location}")
    else:
        prevent = YieldPrevented(frame, reason, False)
        print(f"yields prevented in {location}")

    token = yields_prevented.set(prevent)
    try:
        yield
    finally:
        yields_prevented.reset(token)
