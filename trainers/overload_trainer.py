from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, List
import re

app = FastAPI(title="Progressive Overload Specialist")


class AthleteStateRequest(BaseModel):
    raw_workout_input: str
    parsed_workout_metrics: Dict = {}
    nutrition_rag_context: List[str] = []
    physiological_assessment: str = ""
    next_action_routine: List[str] = []


def parse_workout(text: str):

    text = text.lower()

    # --------------------------------------------------------
    # EXERCISE
    # --------------------------------------------------------

    exercise = "Workout"

    exercise_patterns = [
        ("Bench Press", r"bench\s*press"),
        ("Squat", r"squats?|back\s+squats?"),
        ("Deadlift", r"deadlifts?"),
        ("Overhead Press", r"overhead\s+press"),
        ("Shoulder Press", r"shoulder\s+press"),
        ("Barbell Row", r"barbell\s+rows?"),
        ("Lat Pulldown", r"lat\s+pulldowns?"),
        ("Dumbbell Press", r"dumbbell\s+press"),
    ]

    for name, pattern in exercise_patterns:

        if re.search(pattern, text):
            exercise = name
            break

    # --------------------------------------------------------
    # SETS
    # --------------------------------------------------------

    sets = 0

    match = re.search(
        r"(\d+)\s*(?:sets?|x)",
        text
    )

    if match:
        sets = int(match.group(1))

    # --------------------------------------------------------
    # REPS
    # --------------------------------------------------------

    reps = 0

    patterns = [
        r"(\d+)\s*reps?",
        r"\d+\s*(?:sets?|x)\s*(\d+)",
        r"(\d+)\s*x\s*\d+"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text
        )

        if match:

            try:
                reps = int(match.group(1))
                break
            except:
                pass

    # --------------------------------------------------------
    # WEIGHT
    # --------------------------------------------------------

    weight = 0.0

    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:kg|kilograms?)",
        text
    )

    if match:

        weight = float(
            match.group(1)
        )

    else:

        # pounds → kilograms
        match = re.search(
            r"(\d+(?:\.\d+)?)\s*(?:lbs?|pounds?)",
            text
        )

        if match:

            pounds = float(
                match.group(1)
            )

            weight = round(
                pounds / 2.20462,
                1
            )

    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    if sets == 0:
        sets = 1

    if reps == 0:
        reps = 10

    # --------------------------------------------------------
    # TOTAL VOLUME
    # --------------------------------------------------------

    total_volume = (
        weight *
        reps *
        sets
    )

    # --------------------------------------------------------
    # NEXT TARGET
    # --------------------------------------------------------

    if weight > 0:

        target_weight = round(
            weight + 2.5,
            1
        )

    else:

        target_weight = 10.0

    # --------------------------------------------------------
    # PROGRESSION MESSAGE
    # --------------------------------------------------------

    if weight > 0:

        progression = (
            f"Increase from {weight:g} kg "
            f"to {target_weight:g} kg "
            f"for the next session, "
            f"provided technique remains solid."
        )

    else:

        progression = (
            "Establish a baseline load before "
            "progressing weight."
        )

    return {

        "exercise_detected": exercise,

        "sets": sets,

        "reps": reps,

        "weight_kg": weight,

        "total_volume_kg": total_volume,

        "next_target_weight_kg":
            target_weight,

        "progression_step_kg":
            2.5
    }


@app.post("/overload-plan")
async def overload_plan(
    state: AthleteStateRequest
):

    print(
        "[Overload Node] "
        "Parsing workout metrics..."
    )

    metrics = parse_workout(
        state.raw_workout_input
    )

    exercise = metrics[
        "exercise_detected"
    ]

    sets = metrics["sets"]

    reps = metrics["reps"]

    weight = metrics["weight_kg"]

    volume = metrics[
        "total_volume_kg"
    ]

    target_weight = metrics[
        "next_target_weight_kg"
    ]

    progression = (
        metrics[
            "progression_step_kg"
        ]
    )

    print(
        f"[Overload Node] "
        f"{exercise} | "
        f"{sets} × {reps} @ {weight} kg | "
        f"Volume={volume} kg"
    )

    # --------------------------------------------------------
    # RESPONSE FOR UI + AI
    # --------------------------------------------------------

    return {

        "exercise_detected":
            exercise,

        "sets":
            sets,

        "reps":
            reps,

        "weight_kg":
            weight,

        "total_volume_kg":
            volume,

        "next_target_weight_kg":
            target_weight,

        "progression_step_kg":
            progression,

        "next_action_routine": [

            f"Current Session Volume: "
            f"{volume:g} kg",

            f"Next Session: "
            f"{sets} × {reps} @ "
            f"{target_weight:g} kg",

            f"Progression: +"
            f"{progression:g} kg"
        ],

        "coaching_summary":
            progression
    }


if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8003
    )