import html as html_lib
import random

from nicegui import app, ui

from app.data.session_content import (
    GIST_FEEDBACK,
    MASTERY_QUESTIONS,
    PASSAGE_SECTIONS,
    PASSAGE_TITLE,
    READING_PAUSE_PROMPTS,
    REFLECTION_PROMPT,
    VOCAB_WORDS,
)
from app.supabase_client import (
    complete_session,
    create_session,
    get_active_session,
    save_session_response,
    update_session_step,
)

TOTAL_STEPS = 4
STEP_LABELS = ["Vocab Preview", "Supported Reading", "Gist & Reflection", "Mastery Check"]


@ui.page('/session')
async def session_page():
    if not app.storage.user.get('access_token'):
        return ui.navigate.to('/login')

    user_id = app.storage.user.get('user_id')

    state = {
        'session_id': None,
        'step': 0,          # 0=vocab, 1=reading, 2=gist, 3=mastery
        'vocab_main_queue': list(VOCAB_WORDS),   # words to present first time
        'vocab_retry_queue': [],                  # words missed on first attempt
        'vocab_word_results': {},                 # word -> status string
        'vocab_total_words': len(VOCAB_WORDS),
        'vocab_results': [],   # {word, correct} — kept for legacy compat
        'reading_section': 0,
        'mastery_idx': 0,
        'responses': [],       # all collected response dicts for final save
        'gist_done': False,
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

    def _save_response(step, prompt, answer, feedback, is_correct):
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
                state['session_id'], step, prompt, answer, feedback, is_correct
            )
        except Exception:
            pass

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
        _vocab_within = len(state['vocab_word_results']) / state['vocab_total_words']
        update_progress(0, _vocab_within)
        word = word_data['word']
        sentence = word_data['sentence']
        definition = word_data['definition']
        choices = word_data['choices']
        correct_index = word_data['correct_index']
        total = state['vocab_total_words']
        advanced = {'done': False}

        with content_area:
            if not is_retry:
                ui.label(f'Vocabulary Preview — Word {word_num} of {total}').classes(
                    'text-xs text-gray-400 uppercase tracking-wide'
                )
            else:
                ui.label("Great effort — let's try this one again!").classes(
                    'text-xs text-orange-500 uppercase tracking-wide font-medium'
                )

            with ui.card().classes('w-full p-6 gap-4'):
                # Word — always visible
                ui.label(word).classes('text-3xl font-bold text-primary')

                # Definition — fades out on transition
                def_div = ui.column().classes('gap-1 transition-opacity duration-700')
                with def_div:
                    ui.label(definition).classes(
                        'text-base text-gray-700 leading-relaxed italic'
                    )

                # Example sentence — always visible
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

                # Presentation controls
                ready_div = ui.column().classes('gap-2 items-start')
                with ready_div:
                    ui.label('Read the definition above, then proceed when ready.').classes(
                        'text-sm text-gray-500 italic'
                    )
                    ui.button(
                        "I'm ready →", on_click=lambda: _go_to_question()
                    ).props('color=primary outline')

                # MCQ panel — hidden until definition fades out
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

                # Feedback panel — hidden until answer submitted
                feedback_div = ui.column().classes('gap-3 hidden')

                # Auto-advance to question after 5 seconds (must be created inside
                # a valid element context, so it lives here rather than after the block)
                ui.timer(5.0, lambda: _go_to_question(), once=True)

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
        content_area.clear()
        with content_area:
            with ui.column().classes('items-center w-full gap-6 py-8'):
                ui.label('Vocabulary Preview Complete!').classes('text-2xl font-bold')
                ui.label(f'You mastered {mastered} out of {total} words.').classes(
                    'text-gray-600 text-center text-lg'
                )
                with ui.card().classes('w-full p-4 gap-2'):
                    for wd in VOCAB_WORDS:
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
                        "Don't worry about flagged words — you may see them again in a future session."
                    ).classes('text-sm text-gray-400 italic text-center')
                ui.label(
                    "Now let's read the passage together. Take your time!"
                ).classes('text-gray-500 text-center')
                ui.button(
                    'Start Reading →',
                    on_click=lambda: _go_to_step(1),
                ).props('color=primary')

    def render_reading_step():
        content_area.clear()
        sec_idx = state['reading_section']
        update_progress(1, sec_idx / len(PASSAGE_SECTIONS))

        if sec_idx >= len(PASSAGE_SECTIONS):
            _show_reading_transition()
            return

        section = PASSAGE_SECTIONS[sec_idx]
        pause = READING_PAUSE_PROMPTS[sec_idx]

        with content_area:
            with ui.card().classes('w-full p-5 gap-3'):
                ui.label(f'{PASSAGE_TITLE} — Section {section["section"]} of {len(PASSAGE_SECTIONS)}').classes(
                    'text-xs text-gray-400 uppercase tracking-wide'
                )
                ui.label(section['text']).classes('text-base leading-relaxed')

            with ui.card().classes('w-full p-5 gap-3'):
                ui.label('Reading Check').classes('text-xs text-gray-400 uppercase tracking-wide')
                ui.label(pause['prompt_text']).classes('text-base font-medium')

                answer_input = ui.textarea(placeholder='Your thoughts…').classes('w-full')

                spinner_row = ui.row().classes('items-center gap-2 hidden')
                with spinner_row:
                    ui.spinner(size='sm')
                    ui.label('Processing…').classes('text-sm text-gray-500')

                feedback_col = ui.column().classes('w-full gap-2 hidden')

                submit_btn = ui.button('Submit', on_click=lambda: submit_reading()).props('color=primary')

                def submit_reading(p=pause, inp=answer_input, sp=spinner_row, fb=feedback_col, btn=submit_btn):
                    if not inp.value.strip():
                        ui.notify('Please write something before submitting.', type='warning')
                        return
                    inp.disable()
                    btn.disable()
                    sp.classes(remove='hidden')

                    is_correct = random.random() < 0.5
                    feedback_text = p['dummy_feedback_good'] if is_correct else p['dummy_feedback_miss']

                    def show_feedback():
                        sp.classes(add='hidden')
                        fb.classes(remove='hidden')
                        with fb:
                            icon_name = 'check_circle' if is_correct else 'info'
                            icon_color = 'text-green-600' if is_correct else 'text-blue-500'
                            with ui.row().classes('items-start gap-2'):
                                ui.icon(icon_name).classes(f'{icon_color} text-xl')
                                ui.label(feedback_text).classes('text-sm text-gray-700')
                            ui.button(
                                'Continue Reading →',
                                on_click=lambda: _advance_reading(p, is_correct, feedback_text, inp.value),
                            ).props('color=primary')

                    _save_response('reading_pause', p['prompt_text'], inp.value, feedback_text, is_correct)
                    ui.timer(0.8, show_feedback, once=True)

    def _advance_reading(pause, is_correct, feedback_text, answer):
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

                gist_btn = ui.button('Submit Summary', on_click=lambda: submit_gist()).props('color=primary')

                def submit_gist(inp=gist_input, sp=spinner_row, fb=feedback_col, rc=reflection_col, btn=gist_btn):
                    if not inp.value.strip():
                        ui.notify('Please write a summary before submitting.', type='warning')
                        return
                    inp.disable()
                    btn.disable()
                    sp.classes(remove='hidden')

                    def show_gist_feedback():
                        update_progress(2, 0.5)
                        sp.classes(add='hidden')
                        fb.classes(remove='hidden')
                        with fb:
                            with ui.row().classes('items-start gap-2'):
                                ui.icon('check_circle').classes('text-green-600 text-xl')
                                ui.label(GIST_FEEDBACK['praise']).classes('text-sm text-gray-700')
                            ui.label(f"Also worth noting: {GIST_FEEDBACK['also_note']}").classes(
                                'text-sm text-gray-500 italic'
                            )
                        rc.classes(remove='hidden')

                    _save_response(
                        'gist', 'Gist summary', inp.value, GIST_FEEDBACK['praise'], None
                    )
                    ui.timer(0.8, show_gist_feedback, once=True)

                with reflection_col:
                    ui.separator()
                    ui.label('Reflection').classes('text-xs text-gray-400 uppercase tracking-wide')
                    ui.label(REFLECTION_PROMPT).classes('text-base font-medium')

                    reflection_input = ui.textarea(placeholder='I would ask…').classes('w-full')

                    def advance_from_reflection(rinp=reflection_input):
                        if rinp.value.strip():
                            _save_response('gist', REFLECTION_PROMPT, rinp.value, '', None)
                        _go_to_step(3)

                    ui.button('Continue →', on_click=advance_from_reflection, icon='arrow_forward').props('color=primary')

    def render_mastery_step():
        content_area.clear()
        q_idx = state['mastery_idx']
        update_progress(3, q_idx / len(MASTERY_QUESTIONS))

        if q_idx >= len(MASTERY_QUESTIONS):
            _show_final_summary()
            return

        question = MASTERY_QUESTIONS[q_idx]
        total_q = len(MASTERY_QUESTIONS)

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
                        feedback_text = q['dummy_feedback_correct'] if is_correct else q['dummy_feedback_incorrect']

                        def show_feedback():
                            sp.classes(add='hidden')
                            fb.classes(remove='hidden')
                            with fb:
                                icon_name = 'check_circle' if is_correct else 'cancel'
                                icon_color = 'text-green-600' if is_correct else 'text-red-500'
                                with ui.row().classes('items-start gap-2'):
                                    ui.icon(icon_name).classes(f'{icon_color} text-xl')
                                    ui.label(feedback_text).classes('text-sm text-gray-700')
                                label = 'Next Question →' if state['mastery_idx'] < len(MASTERY_QUESTIONS) - 1 else 'See Results →'
                                ui.button(label, on_click=lambda: _advance_mastery(q, is_correct, feedback_text, sel['value'])).props('color=primary')

                        sp.classes(remove='hidden')
                        _save_response('mastery', q['text'], sel['value'], feedback_text, is_correct)
                        ui.timer(0.8, show_feedback, once=True)

                else:  # short_answer
                    text_input = ui.textarea(placeholder='Write your answer here…').classes('w-full')

                    sa_btn = ui.button('Submit Answer', on_click=lambda: submit_sa()).props('color=primary')

                    def submit_sa(q=question, inp=text_input, sp=spinner_row, fb=feedback_col, btn=sa_btn):
                        if not inp.value.strip():
                            ui.notify('Please write something before submitting.', type='warning')
                            return
                        inp.disable()
                        btn.disable()
                        is_correct = random.random() < 0.5
                        feedback_text = q['dummy_feedback_correct'] if is_correct else q['dummy_feedback_incorrect']

                        def show_feedback():
                            sp.classes(add='hidden')
                            fb.classes(remove='hidden')
                            with fb:
                                icon_name = 'check_circle' if is_correct else 'info'
                                icon_color = 'text-green-600' if is_correct else 'text-blue-500'
                                with ui.row().classes('items-start gap-2'):
                                    ui.icon(icon_name).classes(f'{icon_color} text-xl')
                                    ui.label(feedback_text).classes('text-sm text-gray-700')
                                label = 'Next Question →' if state['mastery_idx'] < len(MASTERY_QUESTIONS) - 1 else 'See Results →'
                                ui.button(label, on_click=lambda: _advance_mastery(q, is_correct, feedback_text, inp.value)).props('color=primary')

                        sp.classes(remove='hidden')
                        _save_response('mastery', q['text'], inp.value, feedback_text, is_correct)
                        ui.timer(0.8, show_feedback, once=True)

    def _advance_mastery(question, is_correct, feedback_text, answer):
        state['mastery_idx'] += 1
        _persist_step()
        render_mastery_step()

    def _show_final_summary():
        update_progress(4, 1.0)
        content_area.clear()

        # Tally mastery score from responses
        mastery_responses = [r for r in state['responses'] if r['step'] == 'mastery']
        mc_correct = sum(1 for r in mastery_responses if r.get('is_correct'))

        # Persist completion to Supabase
        try:
            complete_session(state['session_id'], {'responses': state['responses']})
        except Exception:
            pass
        # Clear stored session_id so next visit starts fresh
        app.storage.user.pop('session_id', None)

        with content_area:
            with ui.column().classes('items-center w-full gap-6 py-8'):
                ui.icon('emoji_events', size='4rem').classes('text-yellow-500')
                ui.label('Session Complete!').classes('text-3xl font-bold text-center')
                ui.label('Solid work on a challenging text!').classes('text-gray-600 text-center text-lg')

                with ui.card().classes('w-full p-4 text-center gap-1'):
                    ui.label('Comprehension Score').classes('text-xs text-gray-400 uppercase tracking-wide')
                    ui.label(f'{mc_correct + 5}/10').classes('text-3xl font-bold text-primary')

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

    # ── Page load: resume or start fresh ─────────────────────────────────────

    def _start_fresh():
        try:
            sid = create_session(user_id)
        except Exception:
            ui.notify('Could not start session. Please try again.', type='negative')
            return
        state['session_id'] = sid
        app.storage.user['session_id'] = sid
        render_vocab_step()

    def _resume_session(existing: dict):
        state['session_id'] = existing['id']
        resumed_step = existing.get('current_step', 0)
        state['step'] = resumed_step
        app.storage.user['session_id'] = existing['id']
        _go_to_step(resumed_step)

    def _show_resume_prompt(existing: dict):
        content_area.clear()
        update_progress(existing.get('current_step', 0))
        with content_area:
            with ui.column().classes('items-center w-full gap-6 py-8'):
                ui.icon('restore', size='3rem').classes('text-primary')
                ui.label('Continue where you left off?').classes('text-2xl font-bold text-center')
                ui.label(
                    f"You have an unfinished session at {STEP_LABELS[existing.get('current_step', 0)]}."
                ).classes('text-gray-600 text-center')
                with ui.row().classes('gap-4'):
                    ui.button('Continue', on_click=lambda: _resume_session(existing), icon='play_arrow').props('color=primary')
                    ui.button('Start Fresh', on_click=_start_fresh).props('flat')

    # Check for existing in-progress session
    try:
        existing = get_active_session(user_id)
    except Exception:
        existing = None

    if existing:
        _show_resume_prompt(existing)
    else:
        _start_fresh()
