import panel as pn
from fastapi import FastAPI, Request, Response
from panel.io.fastapi import add_application
import logging
import time


# Enable verbose logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger('bokeh').setLevel(logging.DEBUG)
logging.getLogger('panel').setLevel(logging.DEBUG)
logging.getLogger('tornado').setLevel(logging.DEBUG)

pn.extension()


app = FastAPI(title="Simple FastAPI + Panel testing tool")

@app.get("/set-large-cookie")
async def set_large_cookie(response: Response):
    """Set a large cookie to test WebSocket header limits"""
    large_value = 'X' * 1500
    response.set_cookie(
        key="test_large_cookie_" + str(time.time_ns()),
        value=large_value,
        max_age=36000,
        path="/",  # Make cookie available to all paths
        samesite="lax"  # Allow cookie to be sent with navigation
    )
    return {"message": "Large cookie set! Now visit /panel to test"}

@app.get("/clear-cookie")
async def clear_cookie(response: Response):
    """Clear the test cookie"""
    response.delete_cookie("test_large_cookie", path="/")
    return {"message": "Cookie cleared"}


@app.middleware("http")
async def log_headers(request: Request, call_next):
    print(f"\n=== Request to {request.url.path} ===")
    print(f"Host header: {request.headers.get('host')}")
    cookie_header = request.headers.get('cookie', '')
    print(f"Cookie header size: {len(cookie_header)} bytes")
    print(f"All headers ({len(str(request.headers))} bytes):")
    for name, value in request.headers.items():
        print(f"  {name}: {value[:100]}..." if len(value) > 100 else f"  {name}: {value}")
    response = await call_next(request)
    return response


@add_application(
    "/panel",
    app=app,
    title="Panel+FastAPI Websocket Debugging",
)
def create_panel_app():
    return pn.Row(pn.pane.Markdown("# 🚀Hello World! 🌎"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")
