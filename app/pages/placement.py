from nicegui import app, ui
from app.data.placement_passages import PLACEMENT_PASSAGES, compute_reading_level
from app.supabase_client import (
    get_placement_progress,
    save_placement_progress,
    save_placement_response,
    delete_placement_progress,
    upsert_profile,
)

TOTAL_QUESTIONS = sum(len(p["questions"]) for p in PLACEMENT_PASSAGES)


@ui.page('/placement')
async def placement_page():
    if not app.storage.user.get('access_token'):
        return ui.navigate.to('/login')

    user_id = app.storage.user.get('user_id')
    access_token = app.storage.user.get('access_token')

    # Load or create progress
    passage_idx = 0
    q_idx = 0
    answers: list[dict] = []

    try:
        progress = get_placement_progress(user_id)
        if progress:
            passage_idx = progress.get('current_passage_index', 0)
            q_idx = progress.get('current_question_index', 0)
            answers = progress.get('answers', []) or []
        else:
            save_placement_progress(user_id, 0, 0, [])
    except Exception:
        pass

    # State held in mutable container so closures can update it
    state = {
        'passage_idx': passage_idx,
        'q_idx': q_idx,
        'answers': answers,
    }

    def questions_answered():
        total = 0
        for pi in range(state['passage_idx']):
            total += len(PLACEMENT_PASSAGES[pi]['questions'])
        total += state['q_idx']
        return total

    with ui.column().classes('items-center w-full max-w-3xl mx-auto p-6 gap-4'):
        ui.label('Placement Reading').classes('text-2xl font-bold')
        progress_label = ui.label('').classes('text-gray-500 text-sm')
        progress_bar = ui.linear_progress(value=0).classes('w-full')
        content_area = ui.column().classes('w-full gap-4')

    def update_progress_ui():
        answered = questions_answered()
        progress_label.set_text(f'Question {answered + 1} of {TOTAL_QUESTIONS}')
        progress_bar.set_value(answered / TOTAL_QUESTIONS)

    def render_current_question():
        content_area.clear()
        pi = state['passage_idx']
        qi = state['q_idx']

        if pi >= len(PLACEMENT_PASSAGES):
            finish()
            return

        passage = PLACEMENT_PASSAGES[pi]
        question = passage['questions'][qi]
        update_progress_ui()

        with content_area:
            with ui.card().classes('w-full p-4 gap-2'):
                ui.label(passage['title']).classes('text-lg font-semibold')
                ui.label(f"Genre: {passage['genre'].capitalize()}  ·  {passage['approximate_lexile']}").classes(
                    'text-xs text-gray-400'
                )
                ui.separator()
                for para in passage['text'].split('\n\n'):
                    ui.label(para).classes('text-base leading-relaxed')

            with ui.card().classes('w-full p-4 gap-3'):
                ui.label(f"Question {qi + 1}").classes('text-xs text-gray-400 uppercase tracking-wide')
                ui.label(question['text']).classes('text-base font-medium')

                if question['type'] == 'multiple_choice':
                    selected = {'value': None}
                    radio_group = ui.radio(
                        options=question['choices'],
                        on_change=lambda e: selected.update(value=e.value),
                    ).classes('gap-2')

                    def submit_mc(q=question, p=passage, sel=selected):
                        if sel['value'] is None:
                            ui.notify('Please select an answer.', type='warning')
                            return
                        is_correct = sel['value'] == q['correct_answer']
                        record = {
                            'passage_id': p['id'],
                            'question_id': q['id'],
                            'answer': sel['value'],
                            'is_correct': is_correct,
                        }
                        state['answers'].append(record)
                        try:
                            save_placement_response(user_id, p['id'], q['id'], sel['value'], is_correct)
                        except Exception:
                            pass
                        advance()

                    ui.button('Submit Answer', on_click=submit_mc).props('color=primary')

                else:  # short_answer
                    text_input = ui.textarea(placeholder='Write your answer here...').classes('w-full')

                    def submit_sa(q=question, p=passage, inp=text_input):
                        answer_text = inp.value.strip()
                        if not answer_text:
                            ui.notify('Please write something before submitting.', type='warning')
                            return
                        record = {
                            'passage_id': p['id'],
                            'question_id': q['id'],
                            'answer': answer_text,
                            'is_correct': None,
                        }
                        state['answers'].append(record)
                        try:
                            save_placement_response(user_id, p['id'], q['id'], answer_text, None)
                        except Exception:
                            pass
                        advance()

                    ui.button('Submit Answer', on_click=submit_sa).props('color=primary')

    def advance():
        pi = state['passage_idx']
        qi = state['q_idx']
        passage = PLACEMENT_PASSAGES[pi]

        next_qi = qi + 1
        if next_qi < len(passage['questions']):
            state['q_idx'] = next_qi
            _persist_progress()
            render_current_question()
        else:
            # End of passage
            next_pi = pi + 1
            state['passage_idx'] = next_pi
            state['q_idx'] = 0
            _persist_progress()
            if next_pi >= len(PLACEMENT_PASSAGES):
                finish()
            else:
                show_interstitial(next_pi)

    def _persist_progress():
        try:
            save_placement_progress(
                user_id,
                state['passage_idx'],
                state['q_idx'],
                state['answers'],
            )
        except Exception:
            pass

    def show_interstitial(next_pi: int):
        content_area.clear()
        update_progress_ui()
        next_passage = PLACEMENT_PASSAGES[next_pi]
        with content_area:
            with ui.column().classes('items-center w-full gap-6 py-8'):
                ui.icon('auto_stories', size='3rem').classes('text-primary')
                ui.label('Great work!').classes('text-2xl font-bold')
                ui.label(
                    f"You've finished passage {next_pi} of {len(PLACEMENT_PASSAGES)}. "
                    "Ready for the next one?"
                ).classes('text-gray-600 text-center')
                ui.label(f"Next up: {next_passage['title']}").classes('text-lg font-semibold')
                ui.button('Continue', on_click=render_current_question, icon='arrow_forward').props('color=primary')

    def finish():
        level, lexile = compute_reading_level(state['answers'])
        app.storage.user['placement_level'] = level
        app.storage.user['placement_lexile'] = lexile
        try:
            upsert_profile(user_id, {
                'onboarded': True,
                'reading_level': level,
            }, access_token=access_token)
        except Exception:
            pass
        try:
            delete_placement_progress(user_id)
        except Exception:
            pass
        ui.navigate.to('/placement-result')

    render_current_question()
