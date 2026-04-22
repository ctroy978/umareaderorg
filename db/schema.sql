CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT,
    password_hash TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS profiles (
    user_id TEXT PRIMARY KEY,
    full_name TEXT,
    email TEXT,
    reading_level TEXT,
    onboarded INTEGER DEFAULT 0,
    interests TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS topic_bank (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    topic TEXT,
    hook TEXT,
    key_facts TEXT
);

CREATE TABLE IF NOT EXISTS session_bundles (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    topic TEXT,
    status TEXT DEFAULT 'generating',
    passage_title TEXT,
    passage_text TEXT,
    passage_sections TEXT,
    vocab_questions TEXT,
    comprehension_questions TEXT,
    mastery_questions TEXT,
    reflection_question TEXT,
    topic_bank_id TEXT,
    strategy_of_session TEXT,
    strategy_chunk_index INTEGER,
    error_message TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    student_id TEXT NOT NULL,
    bundle_id TEXT,
    status TEXT DEFAULT 'in_progress',
    current_step INTEGER DEFAULT 0,
    responses_json TEXT,
    started_at TEXT DEFAULT (datetime('now')),
    completed_at TEXT,
    deleted_at TEXT,
    strategy_of_session TEXT
);

CREATE TABLE IF NOT EXISTS session_responses (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    step TEXT,
    prompt TEXT,
    student_answer TEXT,
    feedback_text TEXT,
    is_correct INTEGER,
    rubric_score INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS placement_progress (
    user_id TEXT PRIMARY KEY,
    current_passage_index INTEGER DEFAULT 0,
    current_question_index INTEGER DEFAULT 0,
    answers TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS placement_responses (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    passage_id TEXT,
    question_id TEXT,
    answer TEXT,
    is_correct INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS passage_library (
    topic_bank_id TEXT NOT NULL,
    lexile_level TEXT NOT NULL,
    passage_title TEXT,
    passage_sections TEXT,
    vocab_questions TEXT,
    mastery_questions TEXT,
    use_count INTEGER DEFAULT 0,
    PRIMARY KEY (topic_bank_id, lexile_level)
);

CREATE TABLE IF NOT EXISTS strategy_lessons (
    id TEXT PRIMARY KEY,
    strategy TEXT NOT NULL,
    reading_level TEXT NOT NULL,
    variation_id INTEGER DEFAULT 1,
    is_active INTEGER DEFAULT 1,
    title TEXT,
    content TEXT,
    example_text TEXT,
    example_application TEXT
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id TEXT PRIMARY KEY,
    student_id TEXT,
    tool_name TEXT,
    input_json TEXT,
    output_json TEXT,
    error_text TEXT,
    duration_ms INTEGER,
    session_id TEXT,
    iteration_count INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);
