from nicegui import app, ui
from app.supabase_client import get_profile


@ui.page('/dashboard')
async def dashboard_page():
    if not app.storage.user.get('access_token'):
        return ui.navigate.to('/login')

    user_id = app.storage.user.get('user_id')
    email = app.storage.user.get('email', 'Student')

    # Try to fetch profile for display name
    display_name = email
    try:
        profile = get_profile(user_id)
        if profile and profile.get('full_name'):
            display_name = profile['full_name']
    except Exception:
        pass

    with ui.column().classes('items-center w-full p-8 gap-4'):
        ui.label(f'Welcome, {display_name}!').classes('text-3xl font-bold')
        ui.label('Your personalized reading dashboard will appear here.').classes('text-gray-500')

        ui.separator()

        def logout():
            app.storage.user.clear()
            ui.navigate.to('/login')

        ui.button('Sign out', on_click=logout, icon='logout')
