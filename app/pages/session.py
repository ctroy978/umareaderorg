import asyncio
import datetime
import html as html_lib
import random

from nicegui import app, ui

from app.supabase_client import (
    complete_session,
    create_session,
    create_session_bundle,
    fail_session_bundle,
    get_active_bundle,
    get_active_session,
    get_profile,
    get_session_bundle,
    get_session_strategy,
    get_strategy_lesson,
    get_today_skip_count,
    save_session_response,
    soft_delete_session,
    update_session_step,
)
from agents.tools.bundle_generator import generate_session_bundle
from agents.tools.feedback_tool import get_feedback
from utils.config import DEFAULT_STRATEGY  # dev override; None in production
from utils.session_code import generate_completion_code, score_to_level, RANK_TITLES, RANK_FEEDBACK, RANK_BLURBS

TOTAL_STEPS = 4
STEP_LABELS = ["Vocab Preview", "Supported Reading", "Gist & Reflection", "Mastery Check"]

_TOPIC_CATEGORIES = [
    {"label": "Science", "value": "science and nature"},
    {"label": "History", "value": "history and historical events"},
    {"label": "Sports", "value": "sports and athletics"},
    {"label": "Animals", "value": "animals and wildlife"},
    {"label": "Technology", "value": "technology and inventions"},
    {"label": "Mystery", "value": "mystery and detective stories"},
    {"label": "Adventure", "value": "adventure and exploration"},
    {"label": "Nature", "value": "environment and ecosystems"},
    {"label": "Space", "value": "space and astronomy"},
    {"label": "Biography", "value": "biography and remarkable people"},
]

# Stuck-bundle timeout: treat 'generating' bundles older than this as failed
_STUCK_BUNDLE_MINUTES = 5


@ui.page('/session')
async def session_page():
    if not app.storage.user.get('access_token'):
        return ui.navigate.to('/login')

    user_id = app.storage.user.get('user_id')
    access_token = app.storage.user.get('access_token')

    state = {
        'session_id': None,
        'bundle_id': None,
        'bundle': None,
        'step': 0,          # 0=vocab, 1=reading, 2=gist, 3=mastery
        'passage_title': None,
        'passage_sections': None,
        'vocab_words': None,
        'vocab_main_queue': [],
        'vocab_retry_queue': [],
        'vocab_word_results': {},
        'vocab_total_words': 0,
        'vocab_results': [],
        'reading_section': 0,
        'mastery_idx': 0,
        'responses': [],
        'gist_done': False,
        'reading_level': '800L',
        '_last_gist': '',
        'strategy_of_session': None,
        'strategy_chunk_index': None,
    }

    # ── Top-level layout ──────────────────────────────────────────────────────
    _CIRCLE_BASE = (
        'width:2rem;height:2rem;border-radius:50%;box-sizing:border-box;transition:all 0.3s ease;'
    )
    _CIRCLE_LABELS = ['Vocab', 'Reading', 'Gist', 'Mastery']

    with ui.column().classes('items-center w-full max-w-3xl mx-auto p-6 gap-4'):
        ui.label('Reading Session').classes('text-2xl font-bold')

        circle_refs = []
        with ui.row().classes('w-full justify-around items-center py-1'):
            for lbl in _CIRCLE_LABELS:
                with ui.column().classes('items-center gap-1'):
                    c = ui.element('div').style(_CIRCLE_BASE + 'border:2px solid #d1d5db;')
                    circle_refs.append(c)
                    ui.label(lbl).classes('text-xs text-gray-400 text-center')

        progress_bar = ui.linear_progress(value=0, show_value=False).classes('w-full')
        content_area = ui.column().classes('w-full gap-4')

    def update_progress(step: int, within: float = 0.0):
        _done    = _CIRCLE_BASE + 'background-color:var(--q-primary);'
        _current = _CIRCLE_BASE + 'border:3px solid var(--q-primary);'
        _future  = _CIRCLE_BASE + 'border:2px solid #d1d5db;'
        for i, c in enumerate(circle_refs):
            c.style(_done if i < step else (_current if i == step else _future))
        progress_bar.set_value(within)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _persist_step():
        try:
            update_session_step(
                state['session_id'],
                state['step'],
                {'vocab_results': state['vocab_results']},
            )
        except Exception:
            pass

    def _compute_rubric_score(quality: str, attempt_count: int) -> int:
        if quality == 'nonsense':
            return 1
        if quality == 'poor':
            return 2
        if quality == 'moderate':
            return 3
        # good: 5 on first attempt, 4 if a second attempt was needed
        return 5 if attempt_count == 1 else 4

    def _save_response(step, prompt, answer, feedback, is_correct, rubric_score=None):
        record = {
            'step': step,
            'prompt': prompt,
            'answer': answer,
            'feedback': feedback,
            'is_correct': is_correct,
        }
        state['responses'].append(record)
        try:
            save_session_response(
                state['session_id'], step, prompt, answer, feedback, is_correct,
                rubric_score=rubric_score,
            )
        except Exception:
            pass

    def _load_bundle_into_state(bundle: dict):
        state['bundle'] = bundle
        state['bundle_id'] = bundle['id']
        state['passage_title'] = bundle['passage_title']
        state['passage_sections'] = bundle['passage_sections']
        vocab = bundle.get('vocab_questions') or []
        state['vocab_words'] = vocab
        state['vocab_main_queue'] = list(vocab)
        state['vocab_total_words'] = len(vocab)
        state['strategy_chunk_index'] = bundle.get('strategy_chunk_index')

    # ── Topic picker ──────────────────────────────────────────────────────────

    def render_topic_picker():
        content_area.clear()
        update_progress(0, 0.0)
        selected_topic = {'value': None}
        all_buttons = []

        with content_area:
            ui.label("What would you like to read about today?").classes('text-xl font-bold text-center')
            ui.label("Choose a category below.").classes('text-gray-500 text-center text-sm')

            with ui.grid(columns=2).classes('w-full gap-3 mt-2'):
                for cat in _TOPIC_CATEGORIES:
                    btn = ui.button(cat['label']).props('outline').classes('w-full')
                    all_buttons.append(btn)

                    def _make_click(val, b):
                        def _click():
                            selected_topic['value'] = val
                            # Reset all buttons to outline, highlight the selected one
                            for other in all_buttons:
                                other.props('outline color=')
                            b.props(remove='outline')
                            b.props('color=primary')
                        return _click

                    btn.on_click(_make_click(cat['value'], btn))

            error_label = ui.label('').classes('text-red-500 text-sm hidden')

            def _on_start():
                topic = selected_topic['value']
                if not topic:
                    error_label.set_text('Please choose a category first.')
                    error_label.classes(remove='hidden')
                    return
                error_label.classes(add='hidden')
                asyncio.create_task(_on_topic_selected(topic))

            ui.button('Start Reading →', on_click=_on_start).props('color=primary').classes('w-full mt-2')

    # ── Loading screen ────────────────────────────────────────────────────────

    def _show_loading_screen(topic: str):
        content_area.clear()
        with content_area:
            with ui.column().classes('items-center w-full gap-4 py-16'):
                ui.spinner(size='xl')
                ui.label('Preparing your session…').classes('text-gray-700 text-xl font-semibold text-center')
                ui.label(f'Topic: {topic}').classes('text-gray-500 text-base text-center')
                ui.label('This may take several minutes. You\'ll only wait once.').classes(
                    'text-gray-400 text-sm text-center italic'
                )

    # ── Topic selected → generate bundle ─────────────────────────────────────

    async def _on_topic_selected(topic: str):
        bundle_id = create_session_bundle(user_id, topic)
        state['bundle_id'] = bundle_id
        _show_loading_screen(topic)

        profile = get_profile(user_id, access_token)
        reading_level = (profile or {}).get('reading_level', '800L')
        state['reading_level'] = reading_level

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: generate_session_bundle(bundle_id, user_id, topic, reading_level, access_token),
        )

        bundle = get_session_bundle(bundle_id)
        if bundle and bundle.get('status') == 'ready':
            _load_bundle_into_state(bundle)
            try:
                # Strategy is set by AI during bundle generation; DEFAULT_STRATEGY overrides for dev testing
                strategy = DEFAULT_STRATEGY or (bundle or {}).get('strategy_of_session')
                sid = create_session(user_id, bundle_id=bundle_id, strategy=strategy)
                state['session_id'] = sid
            except Exception:
                ui.notify('Could not start session. Please try again.', type='negative')
                render_topic_picker()
                return
            render_vocab_step()
        else:
            _show_bundle_error()

    def _show_bundle_error():
        content_area.clear()
        with content_area:
            with ui.column().classes('items-center w-full gap-4 py-16'):
                ui.icon('error_outline', size='3rem').classes('text-red-500')
                ui.label('Something went wrong generating your session.').classes(
                    'text-gray-700 text-lg font-semibold text-center'
                )
                ui.label('Please try again with a different topic.').classes('text-gray-500 text-center')
                ui.button('Try Again', on_click=render_topic_picker).props('color=primary')

    # ── Step renderers ────────────────────────────────────────────────────────

    def render_vocab_step():
        main_q = state['vocab_main_queue']
        retry_q = state['vocab_retry_queue']

        if main_q:
            word_data = main_q.pop(0)
            is_retry = False
            word_num = state['vocab_total_words'] - len(main_q)
        elif retry_q:
            word_data = retry_q.pop(0)
            is_retry = True
            word_num = None
        else:
            _show_vocab_transition()
            return

        _render_vocab_word(word_data, is_retry, word_num)

    def _render_vocab_word(word_data, is_retry, word_num):
        content_area.clear()
        _vocab_within = len(state['vocab_word_results']) / max(state['vocab_total_words'], 1)
        update_progress(0, _vocab_within)
        word = word_data['word']
        sentence = word_data['sentence']
        definition = word_data['definition']
        choices = list(word_data['choices'])
        correct_answer = choices[word_data['correct_index']]
        random.shuffle(choices)
        correct_index = choices.index(correct_answer)
        total = state['vocab_total_words']
        advanced = {'done': False}

        with content_area:
            if not is_retry:
                ui.label(f'Vocabulary Preview — Word {word_num} of {total}').classes(
                    'text-xs text-gray-400 uppercase tracking-wide'
                )
            else:
                ui.label("Let's try this one again!").classes(
                    'text-xs text-orange-500 uppercase tracking-wide font-medium'
                )

            with ui.card().classes('w-full p-6 gap-4'):
                ui.label(word).classes('text-3xl font-bold text-primary')

                def_div = ui.column().classes('gap-1 transition-opacity duration-700')
                with def_div:
                    ui.label(definition).classes(
                        'text-base text-gray-700 leading-relaxed italic'
                    )

                ui.label('Example from the passage:').classes(
                    'text-xs text-gray-400 uppercase tracking-wide mt-2'
                )
                _highlighted = html_lib.escape(sentence).replace(
                    html_lib.escape(word),
                    f'<strong class="text-primary font-bold">{html_lib.escape(word)}</strong>',
                    1,
                )
                ui.html(
                    f'<p class="text-base leading-relaxed text-gray-700">{_highlighted}</p>'
                )

                ui.separator()

                ready_div = ui.column().classes('gap-2 items-start')
                with ready_div:
                    ui.label('Read the definition above, then proceed when ready.').classes(
                        'text-sm text-gray-500 italic'
                    )
                    ui.button(
                        "I'm ready →", on_click=lambda: _go_to_question()
                    ).props('color=primary outline')

                question_div = ui.column().classes('gap-3 hidden')
                with question_div:
                    ui.label(
                        'Which is the best definition of this word in context?'
                    ).classes('text-base font-medium')
                    selected = {'value': None}
                    ui.radio(
                        options=choices,
                        on_change=lambda e: selected.update(value=e.value),
                    ).classes('gap-2')
                    ui.button(
                        'Submit Answer', on_click=lambda: _submit_answer()
                    ).props('color=primary')

                feedback_div = ui.column().classes('gap-3 hidden')

        def _go_to_question():
            if advanced['done']:
                return
            advanced['done'] = True
            def_div.classes(add='opacity-0')
            ready_div.classes(add='hidden')
            ui.timer(0.8, lambda: question_div.classes(remove='hidden'), once=True)

        def _submit_answer():
            if selected['value'] is None:
                ui.notify('Please choose an answer first.', type='warning')
                return
            is_correct = selected['value'] == choices[correct_index]
            question_div.classes(add='hidden')
            feedback_div.classes(remove='hidden')
            feedback_div.clear()
            with feedback_div:
                if is_correct:
                    ui.label('Correct!').classes('text-lg font-bold text-green-600')
                    ui.label(word_data['feedback_correct']).classes(
                        'text-sm text-gray-700 leading-relaxed'
                    )
                else:
                    ui.label('Not quite.').classes('text-lg font-bold text-orange-500')
                    ui.label(word_data['feedback_incorrect']).classes(
                        'text-sm text-gray-700 leading-relaxed'
                    )
                ui.button(
                    'Next →' if is_correct else 'Got it →',
                    on_click=lambda: _handle_result(is_correct),
                ).props('color=primary')
            _save_response(
                'vocab_preview',
                sentence,
                selected['value'],
                word_data['feedback_correct'] if is_correct else word_data['feedback_incorrect'],
                is_correct,
            )
            state['vocab_results'].append({'word': word, 'correct': is_correct})

        def _handle_result(is_correct):
            if is_retry:
                state['vocab_word_results'][word] = (
                    'mastered_retry' if is_correct else 'flagged'
                )
            else:
                if is_correct:
                    state['vocab_word_results'][word] = 'mastered_first'
                else:
                    state['vocab_retry_queue'].append(word_data)
                    state['vocab_word_results'][word] = 'pending_retry'
            _persist_step()
            render_vocab_step()

    def _show_vocab_transition():
        update_progress(0, 1.0)
        total = state['vocab_total_words']
        results = state['vocab_word_results']
        mastered = sum(
            1 for s in results.values() if s in ('mastered_first', 'mastered_retry')
        )
        flagged = [w for w, s in results.items() if s == 'flagged']
        vocab_words = state['vocab_words'] or []
        content_area.clear()
        with content_area:
            with ui.column().classes('items-center w-full gap-6 py-8'):
                ui.label('Vocabulary Preview Complete!').classes('text-2xl font-bold')
                ui.label(f'You mastered {mastered} out of {total} words.').classes(
                    'text-gray-600 text-center text-lg'
                )
                with ui.card().classes('w-full p-4 gap-2'):
                    for wd in vocab_words:
                        w = wd['word']
                        status = results.get(w, 'mastered_first')
                        if status == 'mastered_first':
                            label = f'✓  {w} — Mastered (first try)'
                            color = 'text-green-600'
                        elif status == 'mastered_retry':
                            label = f'✓  {w} — Mastered (on retry)'
                            color = 'text-blue-600'
                        elif status == 'flagged':
                            label = f'○  {w} — Flagged – missed twice'
                            color = 'text-orange-500'
                        else:
                            label = f'•  {w}'
                            color = 'text-gray-500'
                        ui.label(label).classes(f'text-sm font-medium {color}')
                if flagged:
                    ui.label(
                        "Flagged words may appear again in a future session."
                    ).classes('text-sm text-gray-400 italic text-center')
                ui.label(
                    "Now let's read the passage together. Take your time!"
                ).classes('text-gray-500 text-center')
                ui.button(
                    'Start Reading →',
                    on_click=render_mini_lesson_step,
                ).props('color=primary')

    def render_mini_lesson_step():
        """Display the strategy mini-lesson card between vocab and reading.

        Fetches strategy_of_session fresh from the DB so it works for both
        newly-created and resumed sessions. If no strategy is set or no lesson
        is found, skips straight to the reading step.
        """
        try:
            strategy = get_session_strategy(state['session_id'])
        except Exception:
            strategy = None
        state['strategy_of_session'] = strategy

        if not strategy:
            _go_to_step(1)
            return

        try:
            lesson = get_strategy_lesson(strategy, state['reading_level'])
        except Exception:
            lesson = None

        if not lesson:
            _go_to_step(1)
            return

        content_area.clear()
        update_progress(0, 1.0)

        with content_area:
            with ui.column().classes('items-center w-full gap-4 py-4'):
                ui.label("Today's Reading Strategy").classes(
                    'text-xs text-primary uppercase tracking-wide font-medium'
                )
                ui.label(lesson['title']).classes('text-2xl font-bold text-center')

                with ui.card().classes('w-full p-6 gap-4'):
                    ui.markdown(lesson['content']).classes(
                        'text-base leading-relaxed text-gray-700'
                    )

                    if lesson.get('example_text') or lesson.get('example_application'):
                        ui.separator()
                        ui.label('Example').classes(
                            'text-xs text-gray-400 uppercase tracking-wide'
                        )
                        if lesson.get('example_text'):
                            ui.html(
                                f'<p class="text-sm text-gray-600 italic leading-relaxed'
                                f' border-l-4 border-primary pl-3">'
                                f'{html_lib.escape(lesson["example_text"])}</p>'
                            )
                        if lesson.get('example_application'):
                            ui.label(lesson['example_application']).classes(
                                'text-sm text-gray-700 leading-relaxed'
                            )

                ui.label(
                    "Keep this strategy in mind as you read today's passage."
                ).classes('text-gray-500 text-center text-sm italic')

                ui.button(
                    'Start Reading →',
                    on_click=lambda: _go_to_step(1),
                ).props('color=primary')

    def render_reading_step():
        content_area.clear()
        sec_idx = state['reading_section']
        sections = state['passage_sections'] or []
        title = state['passage_title'] or ''
        update_progress(1, sec_idx / max(len(sections), 1))

        if sec_idx >= len(sections):
            _show_reading_transition()
            return

        section = sections[sec_idx]
        bundle = state['bundle'] or {}
        comp_questions = bundle.get('comprehension_questions') or []

        # Load pre-generated question for this section
        if sec_idx < len(comp_questions):
            comp_q = comp_questions[sec_idx]
            prompt_text = comp_q.get('prompt', '')
            rubric = comp_q.get('rubric', '')
        else:
            prompt_text = 'What is this section mainly about?'
            rubric = ''

        with content_area:
            with ui.card().classes('w-full p-5 gap-3'):
                ui.label(f'{title} — Section {section["section"]} of {len(sections)}').classes(
                    'text-xs text-gray-400 uppercase tracking-wide'
                )
                ui.label(section['text']).classes('text-base leading-relaxed')

            with ui.card().classes('w-full p-5 gap-3'):
                ui.label('Reading Check').classes('text-xs text-gray-400 uppercase tracking-wide')
                ui.label(prompt_text).classes('text-base font-medium')
                answer_input = ui.textarea(placeholder='Your thoughts…').classes('w-full')

                spinner_row = ui.row().classes('items-center gap-2 hidden')
                with spinner_row:
                    ui.spinner(size='sm')
                    ui.label('Processing…').classes('text-sm text-gray-500')

                feedback_col = ui.column().classes('w-full gap-2 hidden')

                attempt = {'count': 0, 'first_answer': None, 'quality': 'moderate'}

                def _on_submit_reading():
                    if not answer_input.value.strip():
                        ui.notify('Please write something before submitting.', type='warning')
                        return
                    answer_input.disable()
                    submit_btn.disable()
                    spinner_row.classes(remove='hidden')
                    asyncio.create_task(_evaluate_reading(answer_input.value))

                submit_btn = ui.button(
                    'Submit', on_click=_on_submit_reading
                ).props('color=primary')

        async def _evaluate_reading(student_response: str):
            attempt['count'] += 1
            if attempt['count'] == 1:
                attempt['first_answer'] = student_response
            is_retry = attempt['count'] > 1

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: get_feedback(
                    'comprehension',
                    is_retry=is_retry,
                    section_text=section['text'],
                    question=prompt_text,
                    rubric=rubric,
                    student_response=student_response,
                ),
            )
            feedback_text = result['feedback']
            attempt['quality'] = result['quality']
            spinner_row.classes(add='hidden')
            feedback_col.clear()
            feedback_col.classes(remove='hidden')
            with feedback_col:
                with ui.element('div').classes('w-full rounded-lg bg-blue-50 p-4'):
                    ui.label(feedback_text).classes('text-base leading-relaxed text-gray-800')
                with ui.row().classes('gap-2 mt-2'):
                    if attempt['count'] == 1:
                        def _try_again():
                            answer_input.enable()
                            answer_input.set_value(attempt['first_answer'])
                            submit_btn.enable()
                            feedback_col.classes(add='hidden')
                        ui.button('Try Again', on_click=_try_again).props('flat color=primary')

                    def _continue_reading(fb=feedback_text, sr=student_response):
                        if attempt['count'] >= 2:
                            combined = f"[Attempt 1] {attempt['first_answer']}\n\n[Attempt 2] {sr}"
                        else:
                            combined = sr
                        score = _compute_rubric_score(attempt['quality'], attempt['count'])
                        _save_response('reading_pause', prompt_text, combined, fb, None, rubric_score=score)
                        _advance_reading(prompt_text, fb, combined)

                    ui.button(
                        'Continue Reading →',
                        on_click=_continue_reading,
                    ).props('color=primary')

    def _advance_reading(pause_prompt, feedback_text, answer):
        state['reading_section'] += 1
        _persist_step()
        render_reading_step()

    def _show_reading_transition():
        update_progress(1, 1.0)
        content_area.clear()

        with content_area:
            with ui.column().classes('items-center w-full gap-6 py-8'):
                ui.icon('auto_stories', size='3rem').classes('text-primary')
                ui.label("You've finished the passage!").classes('text-2xl font-bold')
                ui.label(
                    "Now let's see how well you understood the big picture."
                ).classes('text-gray-600 text-center')
                ui.button(
                    'Continue →',
                    on_click=lambda: _go_to_step(2),
                    icon='arrow_forward',
                ).props('color=primary')

    def render_gist_step():
        update_progress(2, 0.0)
        content_area.clear()
        bundle = state['bundle'] or {}
        reflection_question = bundle.get('reflection_question', '')
        full_passage = bundle.get('passage_text', '')

        with content_area:
            with ui.card().classes('w-full p-5 gap-3'):
                ui.label('Gist Summary').classes('text-xs text-gray-400 uppercase tracking-wide')
                ui.label(
                    'In 2–3 sentences, what was the whole passage about? Write in your own words.'
                ).classes('text-base font-medium')

                gist_input = ui.textarea(placeholder='The passage was about…').classes('w-full')

                spinner_row = ui.row().classes('items-center gap-2 hidden')
                with spinner_row:
                    ui.spinner(size='sm')
                    ui.label('Processing…').classes('text-sm text-gray-500')

                feedback_col = ui.column().classes('w-full gap-2 hidden')
                reflection_col = ui.column().classes('w-full gap-3 hidden')

                attempt = {'count': 0, 'first_answer': None, 'quality': 'moderate'}

                gist_btn = ui.button('Submit Summary', on_click=lambda: submit_gist()).props('color=primary')

                def submit_gist():
                    if not gist_input.value.strip():
                        ui.notify('Please write a summary before submitting.', type='warning')
                        return
                    gist_input.disable()
                    gist_btn.disable()
                    spinner_row.classes(remove='hidden')
                    asyncio.create_task(_evaluate_gist(gist_input.value))

                async def _evaluate_gist(gist_text: str):
                    attempt['count'] += 1
                    if attempt['count'] == 1:
                        attempt['first_answer'] = gist_text
                    is_retry = attempt['count'] > 1

                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None,
                        lambda: get_feedback(
                            'gist',
                            is_retry=is_retry,
                            full_passage=full_passage,
                            student_gist=gist_text,
                        ),
                    )
                    feedback_text = result['feedback']
                    attempt['quality'] = result['quality']
                    update_progress(2, 0.5)
                    spinner_row.classes(add='hidden')
                    feedback_col.clear()
                    feedback_col.classes(remove='hidden')
                    with feedback_col:
                        with ui.element('div').classes('w-full rounded-lg bg-blue-50 p-4'):
                            ui.label(feedback_text).classes('text-base leading-relaxed text-gray-800')
                        if attempt['count'] == 1:
                            with ui.row().classes('gap-2 mt-2'):
                                def _try_again():
                                    gist_input.enable()
                                    gist_input.set_value(attempt['first_answer'])
                                    gist_btn.enable()
                                    feedback_col.classes(add='hidden')
                                ui.button('Try Again', on_click=_try_again).props('flat color=primary')

                                def _show_reflection(fb=feedback_text, gt=gist_text):
                                    state['_last_gist'] = gt
                                    score = _compute_rubric_score(attempt['quality'], attempt['count'])
                                    _save_response('gist', 'Gist summary', gt, fb, None, rubric_score=score)
                                    reflection_col.classes(remove='hidden')
                                ui.button('Continue', on_click=_show_reflection).props('color=primary')
                        else:
                            combined = f"[Attempt 1] {attempt['first_answer']}\n\n[Attempt 2] {gist_text}"
                            state['_last_gist'] = gist_text
                            score = _compute_rubric_score(attempt['quality'], attempt['count'])
                            _save_response('gist', 'Gist summary', combined, feedback_text, None, rubric_score=score)
                            reflection_col.classes(remove='hidden')

                with reflection_col:
                    ui.separator()
                    ui.label('Reflection').classes('text-xs text-gray-400 uppercase tracking-wide')
                    ui.label(reflection_question).classes('text-base font-medium')

                    reflection_input = ui.textarea(placeholder='I would ask…').classes('w-full')

                    def advance_from_reflection():
                        if reflection_input.value.strip():
                            _save_response('gist_reflection', reflection_question, reflection_input.value, '', None)
                        _go_to_step(3)

                    ui.button('Continue →', on_click=advance_from_reflection, icon='arrow_forward').props('color=primary')

    def render_mastery_step():
        content_area.clear()
        bundle = state['bundle'] or {}
        questions = bundle.get('mastery_questions') or []
        q_idx = state['mastery_idx']
        update_progress(3, q_idx / max(len(questions), 1))

        if q_idx >= len(questions):
            _show_final_summary()
            return

        question = questions[q_idx]
        total_q = len(questions)

        with content_area:
            with ui.card().classes('w-full p-5 gap-3'):
                ui.label(f'Mastery Check — Question {q_idx + 1} of {total_q}').classes(
                    'text-xs text-gray-400 uppercase tracking-wide'
                )
                ui.label(question['text']).classes('text-base font-medium')

                spinner_row = ui.row().classes('items-center gap-2 hidden')
                with spinner_row:
                    ui.spinner(size='sm')
                    ui.label('Processing…').classes('text-sm text-gray-500')

                feedback_col = ui.column().classes('w-full gap-2 hidden')

                if question['type'] == 'multiple_choice':
                    selected = {'value': None}
                    ui.radio(
                        options=question['choices'],
                        on_change=lambda e: selected.update(value=e.value),
                    ).classes('gap-2')

                    mc_btn = ui.button('Submit Answer', on_click=lambda: submit_mc()).props('color=primary')

                    def submit_mc(q=question, sel=selected, sp=spinner_row, fb=feedback_col, btn=mc_btn):
                        if sel['value'] is None:
                            ui.notify('Please select an answer.', type='warning')
                            return
                        btn.disable()
                        is_correct = q['choices'].index(sel['value']) == q['correct_index']
                        explanation = q.get('explanation') or (
                            'Correct — that matches the passage.' if is_correct
                            else 'Not quite — review the passage for more context.'
                        )
                        qs = questions
                        sp.classes(add='hidden')
                        fb.classes(remove='hidden')
                        with fb:
                            icon_name = 'check_circle' if is_correct else 'cancel'
                            icon_color = 'text-green-600' if is_correct else 'text-red-500'
                            with ui.row().classes('items-start gap-2'):
                                ui.icon(icon_name).classes(f'{icon_color} text-xl')
                                ui.label(explanation).classes('text-sm text-gray-700')
                            label = 'Next Question →' if state['mastery_idx'] < len(qs) - 1 else 'See Results →'
                            ui.button(label, on_click=lambda: _advance_mastery(q, is_correct, explanation, sel['value'])).props('color=primary')
                        _save_response('mastery', q['text'], sel['value'], explanation, is_correct)

                else:  # short_answer
                    text_input = ui.textarea(placeholder='Write your answer here…').classes('w-full')
                    sa_attempt = {'count': 0, 'first_answer': None, 'quality': 'moderate'}

                    sa_btn = ui.button('Submit Answer', on_click=lambda: submit_sa()).props('color=primary')

                    def submit_sa(q=question, inp=text_input, sp=spinner_row, fb=feedback_col, btn=sa_btn):
                        if not inp.value.strip():
                            ui.notify('Please write something before submitting.', type='warning')
                            return
                        inp.disable()
                        btn.disable()
                        sp.classes(remove='hidden')
                        asyncio.create_task(_eval_sa(q, inp.value, sp, fb))

                    async def _eval_sa(q, answer, sp, fb):
                        sa_attempt['count'] += 1
                        if sa_attempt['count'] == 1:
                            sa_attempt['first_answer'] = answer
                        is_retry = sa_attempt['count'] > 1

                        loop = asyncio.get_event_loop()
                        result = await loop.run_in_executor(
                            None,
                            lambda: get_feedback(
                                'mastery_sa',
                                is_retry=is_retry,
                                question=q['text'],
                                source_span=q.get('source_span', ''),
                                key_points=q.get('key_points', []),
                                student_answer=answer,
                            ),
                        )
                        feedback_text = result['feedback']
                        sa_attempt['quality'] = result['quality']
                        sp.classes(add='hidden')
                        fb.clear()
                        fb.classes(remove='hidden')
                        qs = questions
                        with fb:
                            with ui.element('div').classes('w-full rounded-lg bg-blue-50 p-4'):
                                ui.label(feedback_text).classes('text-base leading-relaxed text-gray-800')
                            label = 'Next Question →' if state['mastery_idx'] < len(qs) - 1 else 'See Results →'
                            with ui.row().classes('gap-2 mt-2'):
                                if sa_attempt['count'] == 1:
                                    def _try_again_sa():
                                        text_input.enable()
                                        text_input.set_value(sa_attempt['first_answer'])
                                        sa_btn.enable()
                                        fb.classes(add='hidden')
                                    ui.button('Try Again', on_click=_try_again_sa).props('flat color=primary')

                                def _continue_sa(fb_text=feedback_text, ans=answer):
                                    if sa_attempt['count'] >= 2:
                                        combined = f"[Attempt 1] {sa_attempt['first_answer']}\n\n[Attempt 2] {ans}"
                                    else:
                                        combined = ans
                                    score = _compute_rubric_score(sa_attempt['quality'], sa_attempt['count'])
                                    _save_response('mastery', q['text'], combined, fb_text, None, rubric_score=score)
                                    _advance_mastery(q, None, fb_text, combined)

                                ui.button(label, on_click=_continue_sa).props('color=primary')

    def _advance_mastery(question, is_correct, feedback_text, answer):
        state['mastery_idx'] += 1
        _persist_step()
        render_mastery_step()

    def _show_final_summary():
        update_progress(4, 1.0)
        content_area.clear()

        mastery_responses = [r for r in state['responses'] if r['step'] == 'mastery']
        correct_count = sum(1 for r in mastery_responses if r.get('is_correct') is True)
        total_mc = sum(1 for r in mastery_responses if r.get('is_correct') is not None)

        mastery_score = (correct_count / total_mc) if total_mc > 0 else None
        student_email = app.storage.user.get('email', '')
        completion_code = generate_completion_code(student_email, mastery_score)
        earned_level = score_to_level(mastery_score)

        try:
            complete_session(state['session_id'], {'responses': state['responses']})
        except Exception:
            pass

        # Adaptive level adjustment (fire-and-forget, never blocks UI)
        band_changed = False
        try:
            from app.level_adjuster import run_level_adjustment
            profile = get_profile(user_id, access_token)
            band_changed = run_level_adjustment(user_id, state['session_id'], profile, access_token, strategy=state.get('strategy_of_session'))
        except Exception:
            band_changed = False

        with content_area:
            with ui.column().classes('items-center w-full gap-6 py-8'):
                ui.label('⚔️').style('font-size: 5rem; line-height: 1;')
                ui.label('Session Complete!').classes('text-3xl font-bold text-center')
                if band_changed:
                    ui.label('Level up!').classes('text-green-600 font-semibold text-lg text-center')
                ui.label('You finished the full reading session.').classes('text-gray-600 text-center text-lg')

                with ui.card().classes('w-full p-4 gap-1'):
                    ui.label('Session Rank').classes('text-xs text-gray-400 uppercase tracking-wide text-center')
                    ui.separator()
                    for lvl in range(1, 5):
                        title = RANK_TITLES[lvl]
                        if lvl == earned_level:
                            with ui.row().classes(
                                'w-full items-center px-3 py-2 rounded'
                            ).style('background-color: #1976d2; color: white;'):
                                ui.label('→').classes('font-bold text-lg w-6')
                                ui.label(title).classes('font-bold text-lg tracking-wide')
                        else:
                            with ui.row().classes('w-full items-center px-3 py-1'):
                                ui.label('').classes('w-6')
                                ui.label(title).classes('text-gray-400 text-base')
                    ui.separator()
                    ui.label(RANK_FEEDBACK[earned_level]).classes('text-sm text-center text-gray-600 pt-1')
                    ui.label(RANK_BLURBS[earned_level]).classes('text-xs text-center text-gray-400 italic pt-1')

                with ui.card().classes('w-full p-4 text-center gap-2'):
                    ui.label('Show your teacher this code').classes('text-xs text-gray-400 uppercase tracking-wide')
                    ui.input(value=completion_code).props('readonly outlined dense').classes(
                        'text-center font-mono text-xl font-bold w-full'
                    )
                    ui.button(
                        'Copy Code',
                        icon='content_copy',
                        on_click=lambda: (
                            ui.run_javascript(f"navigator.clipboard.writeText('{completion_code}')"),
                            ui.notify('Code copied!', type='positive'),
                        ),
                    ).props('flat color=primary')

                ui.label('Next session: Something new awaits!').classes(
                    'text-sm text-gray-400 italic text-center'
                )

                ui.button(
                    'Back to Dashboard',
                    on_click=lambda: ui.navigate.to('/dashboard'),
                    icon='home',
                ).props('color=primary')

    def _go_to_step(step: int):
        state['step'] = step
        _persist_step()
        if step == 0:
            render_vocab_step()
        elif step == 1:
            render_reading_step()
        elif step == 2:
            render_gist_step()
        elif step == 3:
            render_mastery_step()

    # ── Resume helpers ────────────────────────────────────────────────────────

    def _show_resume_prompt(existing: dict):
        content_area.clear()
        update_progress(existing.get('current_step', 0))
        bundle_id = existing.get('bundle_id')
        passage_title = ''
        if bundle_id:
            try:
                b = get_session_bundle(bundle_id)
                passage_title = (b or {}).get('passage_title', '') or ''
            except Exception:
                pass

        title_text = f'"{passage_title}"' if passage_title else 'your previous session'

        skip_count = 0
        try:
            skip_count = get_today_skip_count(user_id)
        except Exception:
            pass

        with content_area:
            with ui.column().classes('items-center w-full gap-6 py-8'):
                ui.icon('restore', size='3rem').classes('text-primary')
                ui.label('Continue where you left off?').classes('text-2xl font-bold text-center')
                ui.label(
                    f"You have an unfinished session at {STEP_LABELS[existing.get('current_step', 0)]}: {title_text}."
                ).classes('text-gray-600 text-center')
                with ui.row().classes('gap-4 items-center flex-wrap justify-center'):
                    ui.button('Continue', on_click=lambda: asyncio.create_task(_resume_session(existing)), icon='play_arrow').props('color=primary')
                    if skip_count < 2:
                        def start_over():
                            soft_delete_session(existing['id'], user_id)
                            render_topic_picker()
                        ui.button('Choose a New Topic', on_click=start_over).props('flat')
                    else:
                        ui.label(
                            "You've already switched topics twice today. Please finish this session."
                        ).classes('text-sm text-orange-600 text-center')

    async def _resume_session(existing: dict):
        bundle_id = existing.get('bundle_id')
        if not bundle_id:
            render_topic_picker()
            return

        bundle = get_session_bundle(bundle_id)
        if not bundle or bundle.get('status') != 'ready':
            render_topic_picker()
            return

        state['session_id'] = existing['id']
        state['step'] = existing.get('current_step', 0)
        _load_bundle_into_state(bundle)
        _go_to_step(state['step'])

    # ── Page load entry point ─────────────────────────────────────────────────

    try:
        existing = get_active_session(user_id)
    except Exception:
        existing = None

    if existing and existing.get('bundle_id'):
        # Check for stuck generating bundle
        bundle_id = existing['bundle_id']
        try:
            active_bundle = get_active_bundle(user_id)
            if (active_bundle
                    and active_bundle.get('status') == 'generating'
                    and active_bundle.get('id') == bundle_id):
                created_at_str = active_bundle.get('created_at', '')
                if created_at_str:
                    import datetime as _dt
                    created_at = _dt.datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    age_minutes = (_dt.datetime.now(_dt.timezone.utc) - created_at).total_seconds() / 60
                    if age_minutes > _STUCK_BUNDLE_MINUTES:
                        soft_delete_session(existing['id'], user_id)
                        existing = None
        except Exception:
            pass

    if existing and existing.get('bundle_id'):
        _show_resume_prompt(existing)
    else:
        render_topic_picker()
