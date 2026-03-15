from datetime import datetime, timezone

from nicegui import app, ui
from app.supabase_client import upsert_profile


@ui.page('/placement-result')
async def placement_result_page():
    if not app.storage.user.get('access_token'):
        return ui.navigate.to('/login')

    level = app.storage.user.get('placement_level')
    lexile = app.storage.user.get('placement_lexile')

    if not level:
        return ui.navigate.to('/placement')

    user_id = app.storage.user.get('user_id')
    access_token = app.storage.user.get('access_token')
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        upsert_profile(user_id, {
            'onboarded': True,
            'reading_level': level,
            'placement_completed_at': now_iso,
        }, access_token=access_token)
    except Exception:
        pass

    with ui.column().classes('items-center w-full max-w-lg mx-auto p-8 gap-6 text-center'):
        ui.icon('check_circle', size='4rem').classes('text-green-500')
        ui.label('All done! Great effort.').classes('text-3xl font-bold')
        ui.label(
            "We've finished your placement reading. Here's where you're starting:"
        ).classes('text-gray-600')

        with ui.card().classes('w-full p-6 gap-2'):
            ui.label('Your Reading Level').classes('text-sm text-gray-500 uppercase tracking-wide')
            ui.label(level).classes('text-4xl font-bold text-primary')
            if lexile:
                ui.label(f'Lexile range: {lexile}').classes('text-gray-500')

        ui.label(
            "Every session is tailored to your level, so you'll always be reading at just the right pace."
        ).classes('text-gray-500 text-sm')

        ui.button('Go to My Dashboard', icon='home', on_click=lambda: ui.navigate.to('/dashboard')).classes(
            'w-full text-lg'
        ).props('color=primary')
