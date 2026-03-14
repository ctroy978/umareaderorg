from nicegui import app, ui
from app.supabase_client import get_profile


@ui.page('/dashboard')
async def dashboard_page():
    if not app.storage.user.get('access_token'):
        return ui.navigate.to('/login')

    user_id = app.storage.user.get('user_id')
    email = app.storage.user.get('email', 'Student')

    display_name = email
    reading_level = None
    try:
        profile = get_profile(user_id)
        if profile:
            if profile.get('full_name'):
                display_name = profile['full_name']
            reading_level = profile.get('reading_level')
    except Exception:
        pass

    first_name = display_name.split()[0] if display_name else 'Reader'

    with ui.column().classes('items-center w-full max-w-2xl mx-auto p-8 gap-6'):
        ui.label(f"Hi {first_name}! Ready to read something at your level?").classes('text-3xl font-bold text-center')

        if reading_level:
            with ui.card().classes('w-full p-4 text-center gap-1'):
                ui.label('Your Reading Level').classes('text-xs text-gray-400 uppercase tracking-wide')
                ui.label(reading_level).classes('text-3xl font-bold text-primary')
        else:
            with ui.card().classes('w-full p-4 text-center gap-2'):
                ui.label('Reading level not yet set').classes('text-gray-400')
                ui.button('Take Placement Test', on_click=lambda: ui.navigate.to('/placement'), icon='quiz').props(
                    'color=primary outline'
                )

        ui.button('Start Today\'s Reading Session', icon='menu_book').classes('w-full text-lg').props(
            'color=primary disable'
        )
        ui.label('Reading sessions coming in Phase 3').classes('text-xs text-gray-400')

        ui.separator()

        def logout():
            app.storage.user.clear()
            ui.navigate.to('/login')

        ui.button('Sign out', on_click=logout, icon='logout').props('flat')
