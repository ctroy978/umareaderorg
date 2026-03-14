import importlib

from fastapi import Request
from fastapi.responses import RedirectResponse
from nicegui import app as nicegui_app, ui

# Import pages to register their @ui.page routes
importlib.import_module('app.pages.login')
importlib.import_module('app.pages.dashboard')

from app.supabase_client import exchange_code_for_session
from utils.config import STORAGE_SECRET


@nicegui_app.get('/auth/callback')
async def auth_callback(request: Request):
    code = request.query_params.get('code')
    if not code:
        return RedirectResponse('/login?error=missing_code')
    try:
        result = exchange_code_for_session(code)
        nicegui_app.storage.user.update({
            'access_token': result.session.access_token,
            'refresh_token': result.session.refresh_token,
            'user_id': result.user.id,
            'email': result.user.email,
        })
        return RedirectResponse('/dashboard')
    except Exception as e:
        return RedirectResponse(f'/login?error={e}')


@nicegui_app.get('/')
async def root():
    return RedirectResponse('/login')


def main():
    ui.run(title='Reading Tutor', storage_secret=STORAGE_SECRET, port=8080, reload=False)


if __name__ == '__main__':
    main()
