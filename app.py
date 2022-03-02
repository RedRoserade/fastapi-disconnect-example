"""One solution: Use a decorator to poll for the disconnect"""

import asyncio
from functools import wraps
from typing import Any, Awaitable, Callable
from fastapi import FastAPI, Query, Request, HTTPException

app = FastAPI(title="Disconnect example")


async def disconnect_poller(request: Request, result: Any):
    """
    Poll for a disconnect.
    If the request disconnects, stop polling and return.
    """
    try:
        while not await request.is_disconnected():
            await asyncio.sleep(0.01)

        print("Request disconnected")

        return result
    except asyncio.CancelledError:
        print("Stopping polling loop")


def cancel_on_disconnect(handler: Callable[[Request], Awaitable[Any]]):
    """
    Decorator that will check if the client disconnects,
    and cancel the task if required.
    """

    @wraps(handler)
    async def cancel_on_disconnect_decorator(request: Request, *args, **kwargs):
        sentinel = object()

        # Create two tasks, one to poll the request and check if the
        # client disconnected, and another which is the request handler
        poller_task = asyncio.ensure_future(disconnect_poller(request, sentinel))
        handler_task = asyncio.ensure_future(handler(request, *args, **kwargs))

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
        print("Raising an HTTP error because I was disconnected!!")

        raise HTTPException(503)

    return cancel_on_disconnect_decorator


@app.get("/example")
@cancel_on_disconnect
async def example(
    request: Request,
    wait: float = Query(..., description="Time to wait, in seconds"),
):
    try:
        print(f"Sleeping for {wait:.2f}")

        await asyncio.sleep(wait)

        print("Sleep not cancelled")

        return f"I waited for {wait:.2f}s and now this is the result"
    except asyncio.CancelledError:
        print("Exiting on cancellation")
