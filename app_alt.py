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
            print("Stopping polling loop")

    async def __call__(self, coro: Awaitable[T]) -> T:
        # Create two tasks, one to poll the request and check if the
        # client disconnected, and another which is the request handler
        poller_task = asyncio.ensure_future(self._poll())
        handler_task = asyncio.ensure_future(coro)

        done, pending = await asyncio.wait(
            [poller_task, handler_task], return_when=asyncio.FIRST_COMPLETED
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

        # Return the result if the handler finished first
        if handler_task in done:
            return await handler_task

        # Otherwise, raise an exception
        # This is not exactly needed, but it will prevent
        # validation errors if your request handler is supposed
        # to return something.
        raise asyncio.CancelledError()


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
