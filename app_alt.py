"""Alternative: Use a dependency that will listen for the disconnect; you can then pass a coroutine to it"""

import asyncio
from typing import Any, Awaitable, TypeVar
from fastapi import Depends, FastAPI, Query, Request, HTTPException

app = FastAPI(title="Disconnect example")


T = TypeVar("T")


class CancelOnDisconnect:
    """
    Dependency that can be used to wrap a coroutine,
    to cancel it if the request disconnects
    """

    def __init__(self, request: Request) -> None:
        self.request = request

    async def _poll(self):
        """
        Poll for a disconnect.
        If the request disconnects, stop polling and return.
        """
        try:
            while not await self.request.is_disconnected():
                await asyncio.sleep(0.01)

            print("Request disconnected, exiting poller")
        except asyncio.CancelledError:
            print("Polling loop cancelled")

    async def __call__(self, awaitable: Awaitable[T]) -> T:
        """Run the awaitable and cancel it if the request disconnects"""

        # Create two tasks, one to poll the request and check if the
        # client disconnected, and another which wraps the awaitable
        poller_task = asyncio.ensure_future(self._poll())
        main_task = asyncio.ensure_future(awaitable)

        _, pending = await asyncio.wait(
            [poller_task, main_task], return_when=asyncio.FIRST_COMPLETED
        )

        # Cancel any outstanding tasks
        for t in pending:
            t.cancel()

            try:
                await t
            except asyncio.CancelledError:
                print(f"{t} was cancelled")
            except Exception as exc:
                print(f"{t} raised {exc} when being cancelled")

        # This will:
        # - Raise asyncio.CancelledError if the handler was cancelled
        # - Return the value if it ran to completion
        # - Raise any other stored exception, if the task raised it
        return await main_task


@app.get("/example")
async def example(
    disconnector: CancelOnDisconnect = Depends(CancelOnDisconnect),
    wait: float = Query(..., description="Time to wait, in seconds"),
):
    try:
        print(f"Sleeping for {wait:.2f}")

        await disconnector(asyncio.sleep(wait))

        print("Sleep not cancelled")

        return f"I waited for {wait:.2f}s and now this is the result"
    except asyncio.CancelledError:
        # You have two options here:
        # 1) Raise a custom exception, will be logged with traceback
        # 2) Raise an HTTPException, won't be logged
        # (The client won't see either)

        print("Exiting on cancellation")
        raise HTTPException(503)
