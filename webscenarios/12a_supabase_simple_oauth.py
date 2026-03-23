import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from supabase import create_client, Client, ClientOptions

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_APP_URL"]
SUPABASE_KEY = os.environ["SUPABASE_API_KEY"]
REDIRECT_URI = "http://localhost:8000/auth/callback"

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.urandom(32).hex())


def _supabase_client() -> Client:
    return create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
        ClientOptions(flow_type="pkce"),
    )


@app.get("/")
async def index(request: Request):
    email = request.session.get("email")
    if not email:
        return RedirectResponse("/login")
    return HTMLResponse(f"""
        <h1>Welcome!</h1>
        <p>You are logged in as <strong>{email}</strong></p>
        <a href="/logout">Log out</a>
    """)


@app.get("/login")
async def login(request: Request):
    supabase = _supabase_client()
    resp = supabase.auth.sign_in_with_oauth(
        {"provider": "google", "options": {"redirect_to": REDIRECT_URI}}
    )
    # Persist the PKCE code verifier in the session so it survives the redirect
    storage_key = f"{supabase.auth._storage_key}-code-verifier"
    request.session["code_verifier"] = supabase.auth._storage.get_item(storage_key)
    return RedirectResponse(resp.url)


@app.get("/auth/callback")
async def auth_callback(request: Request, code: str | None = None):
    if not code:
        return RedirectResponse("/login")

    code_verifier = request.session.pop("code_verifier", None)
    if not code_verifier:
        return RedirectResponse("/login")

    supabase = _supabase_client()
    auth_resp = supabase.auth.exchange_code_for_session(
        {"auth_code": code, "code_verifier": code_verifier}
    )

    email = auth_resp.user.email if auth_resp.user else "unknown"
    request.session["email"] = email
    return RedirectResponse("/")


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
