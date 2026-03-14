from nicegui import app, ui
from app.supabase_client import get_client
from utils.config import SITE_URL


@ui.page('/login')
async def login_page(error: str = ''):
    if app.storage.user.get('access_token'):
        return ui.navigate.to('/dashboard')

    client = get_client()

    with ui.card().classes('absolute-center w-96'):
        ui.label('Reading Tutor').classes('text-2xl font-bold text-center w-full')
        ui.separator()

        # Google OAuth
        async def google_login():
            response = client.auth.sign_in_with_oauth({
                "provider": "google",
                "options": {"redirect_to": f"{SITE_URL}/auth/callback"},
            })
            ui.navigate.to(response.url)

        ui.button('Sign in with Google', on_click=google_login, icon='login').classes('w-full')

        ui.separator()
        ui.label('Or sign in with email').classes('text-sm text-gray-500 text-center w-full')

        # Magic link
        email_input = ui.input('Email address', placeholder='you@example.com').classes('w-full')
        status_label = ui.label('').classes('text-sm text-center w-full')

        async def send_magic_link():
            email = email_input.value.strip()
            if not email:
                status_label.set_text('Please enter your email.')
                return
            try:
                client.auth.sign_in_with_otp({
                    "email": email,
                    "options": {"email_redirect_to": f"{SITE_URL}/auth/callback"},
                })
                status_label.set_text('Check your email for a sign-in link!')
                status_label.classes('text-green-600', remove='text-red-600')
            except Exception as e:
                status_label.set_text(f'Error: {e}')
                status_label.classes('text-red-600', remove='text-green-600')

        ui.button('Send magic link', on_click=send_magic_link).classes('w-full')

        if error:
            ui.label(f'Sign-in error: {error}').classes('text-red-600 text-sm text-center w-full')
