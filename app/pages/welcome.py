from nicegui import app, ui
from app.supabase_client import get_profile, get_placement_progress, upsert_profile

INTERESTS = ["Adventure", "Science", "Sports", "Mysteries", "Animals", "History", "Fantasy"]


@ui.page('/welcome')
async def welcome_page():
    if not app.storage.user.get('access_token'):
        return ui.navigate.to('/login')

    user_id = app.storage.user.get('user_id')
    access_token = app.storage.user.get('access_token')

    # If already onboarded, skip to dashboard
    try:
        profile = get_profile(user_id, access_token=access_token)
        if profile and profile.get('onboarded'):
            return ui.navigate.to('/dashboard')
    except Exception:
        pass

    # If a placement test is already in progress, resume it
    try:
        if get_placement_progress(user_id):
            return ui.navigate.to('/placement')
    except Exception:
        pass

    selected_interests: set[str] = set()

    with ui.column().classes('items-center w-full max-w-2xl mx-auto p-8 gap-6'):
        ui.label('Welcome to UmaRead!').classes('text-4xl font-bold text-center')
        ui.label(
            "We're so glad you're here. This is your personal reading space, "
            "built just for you."
        ).classes('text-lg text-gray-600 text-center')
        ui.label(
            "In a moment, you'll take a short placement reading to help us find the right level for you. "
            "There are no wrong answers — just read your best and answer honestly."
        ).classes('text-base text-gray-500 text-center')
        ui.label(
            "First, tell us what you like to read about! Pick as many as you'd like."
        ).classes('text-lg font-semibold text-center')

        checkboxes: dict[str, ui.checkbox] = {}
        with ui.grid(columns=3).classes('gap-2 w-full'):
            for interest in INTERESTS:
                cb = ui.checkbox(interest)
                checkboxes[interest] = cb

        def get_selected():
            return [i for i, cb in checkboxes.items() if cb.value]

        async def start_placement():
            interests = get_selected()
            selected_interests.update(interests)
            try:
                upsert_profile(user_id, {'interests': interests}, access_token=access_token)
            except Exception:
                pass
            ui.navigate.to('/placement')

        async def do_later():
            interests = get_selected()
            try:
                upsert_profile(user_id, {
                    'onboarded': True,
                    'reading_level': 'Level 1',
                    'interests': interests,
                }, access_token=access_token)
            except Exception:
                pass
            ui.navigate.to('/dashboard')

        ui.button('Start My Placement Test', on_click=start_placement, icon='arrow_forward').classes(
            'w-full text-lg'
        ).props('color=primary')
        ui.button("I'll do this later", on_click=do_later).classes('w-full').props('flat color=grey')
