import sys
from contextlib import aclosing

import pytest
from anyio.lowlevel import checkpoint

from pep789 import check_yield, set_yields_prevented

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True, scope="module")
def enable_yield_preventor():
    sys.monitoring.use_tool_id(sys.monitoring.DEBUGGER_ID, "yield_preventor")
    sys.monitoring.set_events(
        sys.monitoring.DEBUGGER_ID, sys.monitoring.events.PY_YIELD
    )
    sys.monitoring.register_callback(
        sys.monitoring.DEBUGGER_ID, sys.monitoring.events.PY_YIELD, check_yield
    )

    yield

    sys.monitoring.free_tool_id(sys.monitoring.DEBUGGER_ID)


class TestGenerator:
    def test_prevent_generator(self):
        def genfunc():
            with set_yields_prevented("test"):
                yield 1

        with pytest.raises(RuntimeError, match="test"):
            for _ in genfunc():
                pass

    def test_prevent_reallow_generator(self):
        def genfunc():
            with set_yields_prevented("test"), set_yields_prevented(None):
                yield 1

        for _ in genfunc():
            pass

    def test_prevent_reallow_prevent_generator(self):
        def genfunc():
            with set_yields_prevented("test"), set_yields_prevented(None):
                with set_yields_prevented("test2"):
                    yield 1

        with pytest.raises(RuntimeError, match="test2"):
            for _ in genfunc():
                pass

    def test_prevent_reallow_prevent_reallow_generator(self):
        def genfunc():
            with set_yields_prevented("test"), set_yields_prevented(None):
                with set_yields_prevented("test2"):
                    pass

                yield 1

        for _ in genfunc():
            pass

    def test_generator_return(self):
        def genfunc():
            yield 1
            with set_yields_prevented("test"):
                return 2

        for _ in genfunc():
            pass

    def test_allow_generator_in_another_frame(self):
        def simplegen():
            yield 1

        def genfunc():
            yield 1
            with set_yields_prevented("test"):
                next(simplegen())

        for _ in genfunc():
            pass


class TestAsyncGenerator:
    async def test_prevent_generator(self):
        async def genfunc():
            await checkpoint()
            with set_yields_prevented("test"):
                yield 1

        with pytest.raises(RuntimeError, match="test"):
            async with aclosing(genfunc()) as gen:
                async for _ in gen:
                    pass

    async def test_prevent_reallow_generator(self):
        async def genfunc():
            with set_yields_prevented("test"), set_yields_prevented(None):
                await checkpoint()
                yield 1
                await checkpoint()

        async with aclosing(genfunc()) as gen:
            async for _ in gen:
                pass

    async def test_prevent_reallow_prevent_generator(self):
        async def genfunc():
            with set_yields_prevented("test"), set_yields_prevented(None):
                await checkpoint()
                with set_yields_prevented("test2"):
                    yield 1

        with pytest.raises(RuntimeError, match="test2"):
            async with aclosing(genfunc()) as gen:
                async for _ in gen:
                    pass

    async def test_prevent_reallow_prevent_reallow_generator(self):
        async def genfunc():
            with set_yields_prevented("test"), set_yields_prevented(None):
                with set_yields_prevented("test2"):
                    pass

                await checkpoint()
                yield 1

        async with aclosing(genfunc()) as gen:
            async for _ in gen:
                pass

    async def test_allow_generator_in_another_frame(self):
        async def simplegen():
            yield 1

        async def genfunc():
            yield 1
            with set_yields_prevented("test"):
                await anext(simplegen())

        async with aclosing(genfunc()) as gen:
            async for _ in gen:
                pass
