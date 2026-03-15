"""
Hard-coded dummy content for a single Phase 3 reading session.
Passage: Deep-sea exploration (~6th-grade stretch text).
"""

PASSAGE_TITLE = "Into the Deep: Exploring the Ocean Floor"

PASSAGE_SECTIONS = [
    {
        "section": 1,
        "text": (
            "More than eighty percent of Earth's oceans remain unexplored. Far below the sunlit "
            "surface, the seafloor stretches across vast plains, towering mountain ranges, and "
            "trenches deeper than Mount Everest is tall. For centuries, humans could only imagine "
            "what lurked in those perpetual shadows. Then came the invention of deep-sea submersibles "
            "— small, reinforced vessels designed to withstand crushing water pressure — and the "
            "ocean floor finally began to give up its secrets."
        ),
    },
    {
        "section": 2,
        "text": (
            "One of the most astonishing discoveries of deep-sea exploration was the existence of "
            "hydrothermal vents. In 1977, scientists piloting the submersible Alvin found superheated "
            "water gushing from cracks in the ocean floor near the Galápagos Islands. Around these "
            "vents, entire ecosystems thrived — tube worms as long as a human arm, ghostly white "
            "crabs, and bacteria that fed not on sunlight but on chemicals dissolved in the scalding "
            "water. This process, called chemosynthesis, overturned the long-held belief that all "
            "life on Earth ultimately depends on the sun."
        ),
    },
    {
        "section": 3,
        "text": (
            "Exploring the deep ocean is extraordinarily difficult. At a depth of four kilometers, "
            "water pressure is roughly four hundred times greater than at sea level — enough to "
            "crush an unprotected human body instantly. Submersibles must be built from titanium "
            "and syntactic foam, materials that resist deformation under immense force. Communication "
            "with the surface is unreliable because radio waves cannot travel through seawater. "
            "Instead, scientists use acoustic signals — pulses of sound — to send data upward. Even "
            "so, a single research dive can take hours just to reach the seafloor."
        ),
    },
    {
        "section": 4,
        "text": (
            "Despite these challenges, deep-sea research has never been more important. The ocean "
            "floor stores vast amounts of carbon dioxide and regulates Earth's climate. Mining "
            "companies are eyeing seafloor mineral deposits, raising urgent questions about whether "
            "harvesting them would destroy ecosystems we barely understand. Scientists argue that "
            "we must map and study the deep ocean before we exploit it, just as we would never "
            "raze a forest without knowing what lived there. In the coming decades, robotic vehicles "
            "and artificial intelligence may finally allow humans to survey the entire ocean floor "
            "— and the discoveries waiting there could reshape our understanding of life itself."
        ),
    },
]

VOCAB_WORDS = [
    {
        "word": "submersible",
        "sentence": "Far below the sunlit surface, deep-sea submersibles — small, reinforced vessels designed to withstand crushing water pressure — allowed humans to explore the ocean floor.",
        "definition": "A small, specially built underwater vehicle designed to travel and operate at extreme ocean depths.",
        "choices": [
            "A type of underwater breathing equipment worn by divers",
            "A small vehicle built to travel and operate at extreme ocean depths",
            "A sonar device used to map the ocean floor from above",
            "A scientific instrument that measures deep-water pressure",
        ],
        "correct_index": 1,
        "feedback_correct": "Exactly right! A submersible is a small underwater vehicle engineered to withstand the crushing pressure of the deep ocean — like a mini-submarine for extreme depths.",
        "feedback_incorrect": "Not quite. A submersible is a small underwater vehicle built to handle extreme water pressure. The passage describes them as 'small, reinforced vessels' — think of a mini-submarine designed for the deep sea.",
    },
    {
        "word": "hydrothermal",
        "sentence": "Scientists found hydrothermal vents — cracks in the ocean floor where superheated water gushes out.",
        "definition": "Related to very hot water that has been heated by Earth's internal energy deep underground.",
        "choices": [
            "Relating to the science of mapping underwater landscapes",
            "Describing creatures that can survive both in water and on land",
            "Relating to very hot water heated by Earth's inner heat",
            "A measure of how deep underwater pressure becomes dangerous",
        ],
        "correct_index": 2,
        "feedback_correct": "Great work! 'Hydro' means water and 'thermal' means heat — hydrothermal describes water that's been superheated by energy from inside the Earth.",
        "feedback_incorrect": "Think about the parts of the word: 'hydro' (water) + 'thermal' (heat). Hydrothermal describes water that has been superheated underground. In the passage, hydrothermal vents are cracks where that scalding water gushes out.",
    },
    {
        "word": "chemosynthesis",
        "sentence": "Bacteria fed not on sunlight but on chemicals dissolved in the scalding water — a process called chemosynthesis.",
        "definition": "A process by which living things produce energy and food using chemical reactions instead of sunlight.",
        "choices": [
            "The way plants convert sunlight into food through their leaves",
            "A process of making energy and food from chemicals instead of sunlight",
            "The study of chemical compounds found in the deep ocean",
            "A type of volcanic reaction that releases heat underwater",
        ],
        "correct_index": 1,
        "feedback_correct": "Correct! Chemosynthesis is how vent organisms make energy using chemicals instead of sunlight — which is why life can survive where no light ever reaches.",
        "feedback_incorrect": "The key is 'chemo' (chemical). Chemosynthesis is like photosynthesis but uses chemical energy instead of sunlight. The passage says vent bacteria 'fed not on sunlight but on chemicals' — that process is chemosynthesis.",
    },
    {
        "word": "syntactic foam",
        "sentence": "Submersibles must be built from titanium and syntactic foam, materials that resist deformation under immense force.",
        "definition": "A strong, lightweight material made of tiny hollow spheres packed in resin, used to help vehicles resist crushing pressure.",
        "choices": [
            "A type of computer program used to guide submarines remotely",
            "A waterproof chemical coating applied to deep-sea equipment",
            "A strong, lightweight material with hollow spheres that resists crushing pressure",
            "A special titanium alloy used in the hulls of deep-sea vehicles",
        ],
        "correct_index": 2,
        "feedback_correct": "Well done! Syntactic foam is packed with tiny air-filled spheres, making it both very light and incredibly strong under pressure — perfect for submersibles facing the deep ocean.",
        "feedback_incorrect": "Syntactic foam is a special material built from tiny hollow spheres embedded in resin. It's both light and strong — the passage says it 'resists deformation under immense force,' which is exactly what deep-sea submersibles need.",
    },
    {
        "word": "acoustic",
        "sentence": "Scientists use acoustic signals — pulses of sound — to send data upward through the water.",
        "definition": "Relating to sound or the way sound waves travel.",
        "choices": [
            "Relating to the faint glow produced by deep-sea creatures",
            "Relating to sound or the way sound waves travel",
            "Describing the electric signals used to power underwater equipment",
            "Relating to the temperature measurement of deep seawater",
        ],
        "correct_index": 1,
        "feedback_correct": "Right! Acoustic relates to sound. The passage even explains this — acoustic signals are 'pulses of sound,' used because radio waves cannot travel through seawater.",
        "feedback_incorrect": "Acoustic relates to sound. The passage actually defines it for you: acoustic signals are described as 'pulses of sound.' Scientists use them underwater because radio waves can't pass through water.",
    },
]

READING_PAUSE_PROMPTS = [
    {
        "section": 1,
        "prompt_text": "Why do you think humans know so little about the deep ocean, even though we've been exploring Earth for thousands of years?",
        "dummy_feedback_good": "Great thinking! The extreme depth, pressure, and darkness make it nearly impossible to explore without special technology.",
        "dummy_feedback_miss": "Think about what makes the deep ocean hard to reach — it's not just far away, it's also under enormous pressure and completely dark.",
    },
    {
        "section": 2,
        "prompt_text": "The text says hydrothermal vents 'overturned' a long-held belief. What belief was overturned, and why does it matter?",
        "dummy_feedback_good": "Excellent! Scientists had always assumed all life depends on sunlight. Finding life powered by chemicals completely changed that view.",
        "dummy_feedback_miss": "The key idea is that before 1977, people thought all life needed the sun. The vent ecosystems proved life can exist without any sunlight at all.",
    },
    {
        "section": 3,
        "prompt_text": "In your own words, describe two specific challenges that make deep-sea exploration so difficult.",
        "dummy_feedback_good": "Well done — you identified real engineering challenges. Pressure and communication are the two biggest obstacles scientists face.",
        "dummy_feedback_miss": "Try focusing on specific details: the passage mentions water pressure, building materials, and communication problems as the main obstacles.",
    },
    {
        "section": 4,
        "prompt_text": "The author compares mining the seafloor to razing a forest. What point is the author making with this comparison?",
        "dummy_feedback_good": "Spot on! The comparison shows that destroying an ecosystem before understanding it is reckless — whether on land or at sea.",
        "dummy_feedback_miss": "The author's point is about risk: just like we wouldn't cut down a forest without knowing what lives there, we shouldn't mine the seafloor blindly.",
    },
]

GIST_FEEDBACK = {
    "praise": "Good summary! You captured the main idea that the deep ocean is largely unexplored and that scientists are making surprising discoveries there.",
    "also_note": "Also worth mentioning: the passage emphasizes that deep-sea research matters for the future — both for understanding life and protecting ecosystems from mining.",
}

REFLECTION_PROMPT = "If you could ask a deep-sea scientist one question after reading this passage, what would it be and why?"

MASTERY_QUESTIONS = [
    {
        "id": "m1",
        "type": "multiple_choice",
        "text": "According to the passage, what made hydrothermal vent ecosystems so surprising to scientists?",
        "choices": [
            "They contained minerals worth billions of dollars.",
            "Living things there did not need sunlight to survive.",
            "They were located deeper than anyone had expected.",
            "The water temperature was cooler than the surrounding ocean.",
        ],
        "correct_index": 1,
        "dummy_feedback_correct": "Correct! The vent organisms used chemosynthesis — getting energy from chemicals, not sunlight — which overturned a core assumption about life.",
        "dummy_feedback_incorrect": "Not quite. The passage explains that the big surprise was that organisms survived without any sunlight by using chemical energy instead.",
    },
    {
        "id": "m2",
        "type": "multiple_choice",
        "text": "Which statement best describes why the author thinks the ocean floor should be studied before it is mined?",
        "choices": [
            "Mining technology is not yet advanced enough to work underwater.",
            "The minerals on the seafloor are not actually valuable.",
            "We could destroy ecosystems we do not yet understand.",
            "Governments have already passed laws banning seafloor mining.",
        ],
        "correct_index": 2,
        "dummy_feedback_correct": "Exactly right! The author's concern is that mining could wipe out unknown species and disrupt ecosystems before science has a chance to study them.",
        "dummy_feedback_incorrect": "Re-read the last paragraph. The author's argument is about protecting ecosystems — we risk destroying things we don't even know exist yet.",
    },
    {
        "id": "m3",
        "type": "short_answer",
        "text": "In your own words, explain how chemosynthesis is different from photosynthesis, using evidence from the passage.",
        "dummy_feedback_correct": "Great response! You used evidence from the text and explained the key difference — energy source (chemicals vs. sunlight) — clearly.",
        "dummy_feedback_incorrect": "Good effort! Make sure to mention the key contrast: photosynthesis uses sunlight, while chemosynthesis uses chemicals from the water. Both produce energy for organisms.",
    },
]
