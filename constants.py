"""
Standalone constants for cloud annotation dashboard.
Mirrors src/utils/constants.py but with zero heavy dependencies.
Updated to match Coach Mehdi's "Data analysis.pdf" taxonomy.
"""

# 10 WT Sparring Technique Classes (pipeline model output)
TECHNIQUE_CLASSES = {
    0: "dollyo_chagi",
    1: "ap_chagi",
    2: "yeop_chagi",
    3: "dwit_chagi",
    4: "naeryo_chagi",
    5: "dwi_huryeo_chagi",
    6: "momtong_jireugi",
    7: "cut_kick",
    8: "block_defense",
    9: "neutral_stance",
}

TECHNIQUE_NAMES_REVERSE = {v: k for k, v in TECHNIQUE_CLASSES.items()}

# Display names — Coach Mehdi's shorthand (from PDF)
TECHNIQUE_DISPLAY_NAMES = {
    # Pipeline classes
    "dollyo_chagi": "Dolyo",
    "ap_chagi": "Apchagi",
    "yeop_chagi": "Anchagi",
    "dwit_chagi": "Tichagi",
    "naeryo_chagi": "Neryo",
    "dwi_huryeo_chagi": "Hook",
    "momtong_jireugi": "Punch",
    "cut_kick": "Cut",
    "block_defense": "Block",
    "neutral_stance": "Neutral",
    # Coach Mehdi extra techniques (annotation-only, not in pipeline)
    "makloub": "Makloub",
    "sweep": "Sweep",
    "360_kick": "360",
    "scorpion": "Scorpion",
    "double_anchagi": "Double Anchagi",
    "apal_min_foug": "Apal Min Foug",
    "double": "Double",
}

# Techniques grouped by Coach Mehdi's PDF categories
TECHNIQUE_GROUPS = {
    "Front": ["ap_chagi", "naeryo_chagi", "momtong_jireugi"],
    "Cut": ["cut_kick"],
    "Circular": ["dollyo_chagi", "dwi_huryeo_chagi", "yeop_chagi"],
    "Turning": ["dwit_chagi", "makloub", "sweep", "360_kick", "scorpion"],
    "Unclassified": ["double_anchagi", "double", "apal_min_foug",
                      "block_defense", "neutral_stance"],
}

# Spinning techniques (score double)
SPINNING_TECHNIQUES = {"dwit_chagi", "dwi_huryeo_chagi", "360_kick", "scorpion"}

# WT Scoring
WT_SCORING = {
    "punch_trunk": 1,
    "kick_trunk": 2,
    "kick_head": 3,
    "spinning_kick_trunk": 4,
    "spinning_kick_head": 5,
}

# ── Coach Mehdi's 9 annotation layers (from "Data analysis.pdf") ──
# Layer order: 1=Attitude, 2=Stance, 3=Role, 4=Type, 5=Leg,
#              6=Technique, 7=Target, 8=Value, 9=Penalty
DIMENSION_OPTIONS = {
    "attitude": ["Forward", "Stationary", "Backward"],
    "guard_stance": ["Right Close", "Right Open", "Left Open", "Left Close"],
    "role": ["Attack", "Contre Attack", "Defence"],
    "action_type": ["Single", "Combination"],
    "leg_used": ["Front", "Back", "Right", "Left"],
    "target_zone": ["Head", "Body"],
    "scoring_value": ["No score", "1", "2", "3", "4", "6",
                       "-1", "-2", "-3", "-4", "-6"],
    "penalty": [
        "None",
        "Fall (-1)", "Out (-1)", "Avoid (-1)", "Grab (-1)",
        "After Kalyo (-1)", "Hit below waist (-1)",
        "Kicking falling opponent (-1)", "Misconduct (-1)",
        "Fall 10 sec (-2)", "Out 10 sec (-2)", "Avoid 10 sec (-2)",
        "Apal min foug",
    ],
}

# Fighter colors
FIGHTER_COLORS = {
    "red": {"label": "RED (Hong)", "hex": "#dc3545", "bg": "rgba(220,53,69,0.15)"},
    "blue": {"label": "BLUE (Chung)", "hex": "#0077B6", "bg": "rgba(0,119,182,0.15)"},
}
