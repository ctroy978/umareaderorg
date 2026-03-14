# Reading Tutor App Overview for AI Coder

**App Name (Working Title):** Personal Reading Tutor (or similar – TBD)

**Target Users:** Students in 5th grade and above (upper elementary through middle/high school). The app is **not** intended for younger children (K-4). It focuses on building advanced reading skills like comprehension of complex texts, vocabulary in context, inference, summarization, and handling challenging (stretch) material.

**Core Purpose:**  
The app acts as an always-available **personal AI reading tutor** that helps students improve reading ability through short, daily, structured reading sessions. It uses evidence-based methods (drawn from sources like the IES What Works Clearinghouse Practice Guide on Providing Reading Interventions for Students in Grades 4–9) to deliver personalized, adaptive practice. The emphasis is on:

- Exposing students to appropriately challenging texts ("stretch" reading).
- Removing key barriers (especially vocabulary) without dumbing down the material.
- Providing gentle, explanatory feedback on responses.
- Keeping sessions positive, low-frustration, and completable every time.
- Collecting performance data to gradually adjust difficulty over time.

The app simulates a 1:1 human tutor: patient, encouraging, immediate but non-forcing feedback, and adaptive based on patterns across sessions (not mid-session retries).

**High-Level How the App Works with the Student**

1. **Initial Placement & Onboarding**  
   - Student takes a one-time (or periodic) placement assessment: short adaptive reading passages with comprehension questions (literal, inferential, vocabulary-in-context, main idea).  
   - AI estimates reading level (e.g., approximate Lexile band or internal level 1–5).  
   - Student answers a quick interest survey (topics like science, adventure, history, sports, mysteries) to personalize future texts.  
   - App sets baseline and recommends starting point.

2. **Daily/Regular Sessions (Core Experience – ~30 minutes)**  
   Each session follows a simple, repeatable structure focused on one main "stretch text" (a passage or short article ~100 Lexile points above the student's current estimated level for controlled challenge).  

   **Session Flow (Text-Based Interaction Only):**

   - **Step 1: Targeted Vocabulary Preview (5–7 minutes)**  
     AI selects 4–6 potentially difficult Tier 2 words (high-utility academic words) from the upcoming text.  
     For each word:  
     - Shows the **exact sentence** from the text where it appears.  
     - Asks student to guess the meaning based on context (student types short response).  
     - If guess is good → positive confirmation.  
     - If not → politely says it's not quite right, gives brief clear explanation in context (e.g., "Not quite — here it means advanced and well-designed because..."), then moves to next word **without retry**.  
     After all words:  
     - If ≥90% correct first pass → use original text.  
     - Otherwise → one recycle round for missed words (new sentences).  
     - If still below 90% after recycle → automatically replace failed words with easier synonym/phrase in the displayed text (keeps stretch level overall).  

   - **Step 2: Supported Stretch Reading + Light Comprehension Coaching (15 minutes)**  
     Student reads the prepared full text silently on screen (broken into sections if needed).  
     AI inserts 3–4 short pauses at natural breaks.  
     At each pause: asks **one** focused prompt (varies by session/day, e.g., "Summarize this section in one sentence," "What can you infer about X and why?," "What question do you have now?").  
     Student types response.  
     AI gives immediate feedback:  
     - Good response → affirm and praise briefly.  
     - Incorrect/incomplete → politely note it's not quite accurate, explain why briefly (with text reference if helpful), then move on **without requiring correction or retry**.  
     Goal: keep momentum; never stall session.

   - **Step 3: Quick Gist & Reflection (5–6 minutes)**  
     Student types 2–3 sentence summary (gist) of the whole text.  
     AI compares to model: praises what's captured, notes major misses briefly with explanation, moves on.  
     One short reflection question (e.g., "Which preview word helped most?" or "What felt easiest/hardest?").

   - **Step 4: Mastery Check & Wrap-Up (2–3 minutes)**  
     2–3 quick questions on key ideas/vocabulary from text.  
     For each: student answers → AI scores, gives brief feedback (affirm correct; explain incorrect briefly), moves to next **without retry**.  
     Shows session summary (e.g., "Solid effort on a tough text! You got X/ Y on comprehension.").  
     Teases next session (topic + focus).

3. **Key Interaction Rules (Non-Negotiable for Student Experience)**  
   - **Feedback is always explanatory but never punitive**: "Good try — here's why that's not quite it..."  
   - **No forcing correct answers**: Explain error → move on immediately. Student always finishes the full session.  
   - **No voice/speech input** — everything is text-based (typing responses).  
   - **Positive & encouraging tone** throughout.  
   - **Adaptive over time**: Use aggregated data (accuracy trends across sessions, common error types, completion rates) to adjust:  
     - Increase/decrease stretch level (Lexile/target difficulty).  
     - Adjust number of vocab words (e.g., 3–4 if struggling).  
     - Rotate comprehension focus (gist one day, inference next, question generation later).  
     - Suggest re-placement if big progress/regression.

4. **Overall Student Journey & Motivation**  
   - Short daily sessions build habit.  
   - Progress dashboard shows growth (e.g., level increases, words mastered, comprehension trends).  
   - Simple badges/rewards for consistency/completion (not perfection).  
   - Texts are age-appropriate, interesting, varied (narrative + informational).  
   - App generates or curates safe, leveled passages (copyright-aware).

**Bottom Line for the AI Coder**  
Build a conversational, text-based tutor that guides students through structured 30-minute reading sessions centered on stretch texts. Prioritize flow, positivity, and completion: give helpful explanations for mistakes but never block progress. Collect clean performance data to make smart, gradual adjustments session-to-session. Keep it simple, reliable, and focused on real reading growth for 5th grade+ students.

This is the functional blueprint — the "what" and "how it feels to the student." Code architecture, prompts, data models, etc., come in later phases.
