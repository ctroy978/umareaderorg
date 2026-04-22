from nicegui import app, ui

from app.supabase_client import (
    authenticate_user,
    has_password,
    is_enrolled,
    set_password,
    get_profile,
)
from app.supabase_client import _row, get_conn
from utils.config import TEACHER_EMAILS


def _get_user_id(email: str) -> str | None:
    row = _row(None, "SELECT id FROM users WHERE email=?", (email.strip().lower(),))
    return row["id"] if row else None


@ui.page('/login')
async def login_page():
    if app.storage.user.get('access_token'):
        return ui.navigate.to('/dashboard')

    state = {'email': ''}

    with ui.card().classes('absolute-center w-96 gap-4'):
        ui.label('uMaRead').classes('text-2xl font-bold text-center w-full')
        ui.separator()

        container = ui.column().classes('w-full gap-3')

        def show_email_step():
            container.clear()
            with container:
                ui.label('Sign In').classes('text-lg font-semibold')
                email_input = ui.input(
                    'School email address',
                    placeholder='you@school.edu',
                ).props('outlined').classes('w-full')
                status = ui.label('').classes('text-sm text-center w-full')

                def on_continue():
                    email = email_input.value.strip().lower()
                    if not email:
                        status.set_text('Please enter your email address.')
                        status.classes('text-red-500', remove='text-gray-500')
                        return
                    if not is_enrolled(email):
                        status.set_text("Your email isn't in the system yet — ask your teacher to add you.")
                        status.classes('text-red-500', remove='text-gray-500')
                        return
                    state['email'] = email
                    if has_password(email):
                        show_password_step()
                    else:
                        show_create_password_step()

                email_input.on('keydown.enter', lambda: on_continue())
                ui.button('Continue', on_click=on_continue).props('color=primary').classes('w-full')

        def show_password_step():
            container.clear()
            with container:
                ui.label(f'Welcome back').classes('text-lg font-semibold')
                ui.label(state['email']).classes('text-sm text-gray-500')
                password_input = ui.input(
                    'Password',
                    password=True,
                    password_toggle_button=True,
                ).props('outlined').classes('w-full')
                status = ui.label('').classes('text-sm text-center w-full')

                def on_login():
                    result = authenticate_user(state['email'], password_input.value)
                    if not result:
                        status.set_text('Incorrect password. Please try again.')
                        status.classes('text-red-500', remove='text-gray-500')
                        password_input.set_value('')
                        return
                    _complete_login(result)

                password_input.on('keydown.enter', lambda: on_login())
                ui.button('Log In', on_click=on_login).props('color=primary').classes('w-full')
                ui.button('← Back', on_click=show_email_step).props('flat').classes('w-full')

        def show_create_password_step():
            container.clear()
            with container:
                ui.label('Create your password').classes('text-lg font-semibold')
                ui.label(state['email']).classes('text-sm text-gray-500')
                ui.label('First time here? Set a password to get started.').classes('text-sm text-gray-400')
                pw1 = ui.input(
                    'Password',
                    password=True,
                    password_toggle_button=True,
                ).props('outlined').classes('w-full')
                pw2 = ui.input(
                    'Confirm password',
                    password=True,
                    password_toggle_button=True,
                ).props('outlined').classes('w-full')
                status = ui.label('').classes('text-sm text-center w-full')

                def on_create():
                    p1 = pw1.value
                    p2 = pw2.value
                    if len(p1) < 8:
                        status.set_text('Password must be at least 8 characters.')
                        status.classes('text-red-500', remove='text-green-600')
                        return
                    if p1 != p2:
                        status.set_text("Passwords don't match.")
                        status.classes('text-red-500', remove='text-green-600')
                        return
                    user_id = _get_user_id(state['email'])
                    if not user_id:
                        status.set_text('Something went wrong. Please refresh and try again.')
                        status.classes('text-red-500', remove='text-green-600')
                        return
                    set_password(user_id, p1)
                    result = authenticate_user(state['email'], p1)
                    _complete_login(result, first_time=True)

                pw2.on('keydown.enter', lambda: on_create())
                ui.button('Create Password', on_click=on_create).props('color=primary').classes('w-full')
                ui.button('← Back', on_click=show_email_step).props('flat').classes('w-full')

        def _complete_login(result, first_time: bool = False):
            app.storage.user.update({
                'access_token': result.session.access_token,
                'refresh_token': result.session.refresh_token,
                'user_id': result.user.id,
                'email': result.user.email,
            })
            if result.user.email.lower() in TEACHER_EMAILS:
                ui.navigate.to('/teacher')
                return
            if first_time:
                ui.navigate.to('/welcome')
                return
            try:
                profile = get_profile(result.user.id)
                if profile and (profile.get('onboarded') or profile.get('reading_level')):
                    ui.navigate.to('/dashboard')
                    return
            except Exception:
                pass
            ui.navigate.to('/welcome')

        show_email_step()
