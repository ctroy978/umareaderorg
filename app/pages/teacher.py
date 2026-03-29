from nicegui import app, ui

from app.supabase_client import list_all_users
from utils.config import SESSION_CODE_SECRET, TEACHER_EMAILS
from utils.session_code import LEVEL_LABELS, _email_hash, _compute_hmac


@ui.page('/teacher')
async def teacher_page():
    if not app.storage.user.get('access_token'):
        return ui.navigate.to('/login')

    email = app.storage.user.get('email', '').lower()
    if email not in TEACHER_EMAILS:
        with ui.column().classes('items-center w-full max-w-md mx-auto p-8 gap-4'):
            ui.icon('lock', size='3rem').classes('text-red-400')
            ui.label('Access Denied').classes('text-2xl font-bold')
            ui.label('This page is for teachers only.').classes('text-gray-500')
            ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard')).props('color=primary')
        return

    result_area = None
    code_input = None

    def decode_code():
        code = (code_input.value or '').strip().upper()
        result_area.clear()

        with result_area:
            if not code:
                ui.label('Please enter a code.').classes('text-gray-400 text-sm')
                return

            parts = code.split('-')
            if len(parts) != 4:
                ui.label('Invalid format — expected 4 segments separated by dashes.').classes('text-red-500')
                return

            level_seg, email_hash_seg, nonce_seg, mac_seg = parts

            if len(level_seg) != 2 or level_seg[0] != 'L' or level_seg[1] not in '1234':
                ui.label(f'Invalid level segment "{level_seg}" — expected L1, L2, L3, or L4.').classes('text-red-500')
                return

            if len(email_hash_seg) != 6 or len(nonce_seg) != 6 or len(mac_seg) != 6:
                ui.label('Invalid segment lengths — code may be incomplete or mistyped.').classes('text-red-500')
                return

            level = int(level_seg[1])

            # Find matching student(s) by email hash
            try:
                users = list_all_users()
            except Exception as e:
                ui.label(f'Error fetching student list: {e}').classes('text-red-500')
                return

            hash_matched = [u for u in users if _email_hash(u['email']) == email_hash_seg]

            # Verify HMAC for each candidate
            verified = []
            for u in hash_matched:
                expected_mac = _compute_hmac(level, nonce_seg, u['email'], SESSION_CODE_SECRET)
                if mac_seg == expected_mac:
                    verified.append(u)

            # Display result
            with ui.card().classes('w-full p-4 gap-3'):
                if verified:
                    ui.icon('verified', size='2rem').classes('text-green-500 mx-auto')
                    ui.label('Valid Code').classes('text-green-600 font-bold text-lg text-center')
                elif hash_matched:
                    ui.icon('warning', size='2rem').classes('text-red-500 mx-auto')
                    ui.label('Invalid — HMAC failed').classes('text-red-500 font-bold text-lg text-center')
                    ui.label('Code may be tampered or mistyped.').classes('text-gray-500 text-sm text-center')
                else:
                    ui.icon('help_outline', size='2rem').classes('text-orange-400 mx-auto')
                    ui.label('Unknown Student').classes('text-orange-500 font-bold text-lg text-center')
                    ui.label('No registered student matches this code.').classes('text-gray-500 text-sm text-center')

                ui.separator()

                level_text = LEVEL_LABELS.get(level, str(level))
                with ui.row().classes('w-full justify-between items-center'):
                    ui.label('Level').classes('text-xs text-gray-400 uppercase')
                    ui.label(f'{level} — {level_text}').classes('font-semibold')

                student_list = verified if verified else hash_matched
                if student_list:
                    for u in student_list:
                        name = u.get('full_name') or ''
                        student_email = u.get('email') or ''
                        display = f'{name} ({student_email})' if name else student_email
                        with ui.row().classes('w-full justify-between items-center'):
                            ui.label('Student').classes('text-xs text-gray-400 uppercase')
                            ui.label(display).classes('font-semibold')

    with ui.column().classes('items-center w-full max-w-lg mx-auto p-8 gap-6'):
        with ui.row().classes('w-full items-center justify-between'):
            ui.label('Decode Session Code').classes('text-2xl font-bold')
            ui.button('Dashboard', icon='home', on_click=lambda: ui.navigate.to('/dashboard')).props('flat color=primary')

        ui.label(
            'Enter the code a student gave you to see their identity and performance level.'
        ).classes('text-gray-500 text-sm text-center')

        with ui.card().classes('w-full p-4 gap-3'):
            code_input = ui.input(
                placeholder='e.g. L3-AB3KQ7-F4A91C-3ZXQM2',
            ).props('outlined clearable').classes('w-full font-mono text-lg')
            ui.button('Decode', icon='search', on_click=decode_code).props('color=primary').classes('w-full')

        result_area = ui.column().classes('w-full gap-2')
        with result_area:
            ui.label('Enter a code above to get started.').classes('text-gray-400 text-sm text-center')
