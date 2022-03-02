# FastAPI disconnect example

This repository contains two examples on how to implement a cancellation when the client disconnects.

You have two app scripts: [app.py](./app.py) and [app_alt.py](./app_alt.py), with two different approaches.

Finally, you have a poor man's unit test, [test.py](./test.py), which will call the APIs. It doesn't use FastAPI's TestClient so that it's app-agnostic. 

The test will do two checks: 

- One with a longer wait period than request timeout, this will cause the request handler to be cancelled
- One with a shorter wait period than request timeout, this shouldn't cause cancellations

To run this, after installing the requirements:

- Start the desired app with uvicorn using the default port 8000
- Launch the test
