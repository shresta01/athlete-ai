from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Dict, List


app = FastAPI(
    title="Biomechanics & Form Specialist"
)


class AthleteStateRequest(BaseModel):

    raw_workout_input: str

    parsed_workout_metrics: Dict = Field(
        default_factory=dict
    )

    nutrition_rag_context: List[str] = Field(
        default_factory=list
    )

    physiological_assessment: str = ""

    next_action_routine: List[str] = Field(
        default_factory=list
    )


@app.post("/audit-form")
async def audit_form(
    state: AthleteStateRequest
):

    print(
        "[Biomechanics Node] "
        "Analyzing movement..."
    )

    raw_input = (
        state.raw_workout_input.lower()
    )


    # Default
    parsed_metrics = {

        "exercise_detected":
            "Unknown",

        "sets":
            1,

        "reps":
            10,

        "weight_kg":
            0.0
    }

    assessment = (
        "Form analysis complete. "
        "Maintain controlled movement "
        "and proper bracing."
    )


    # ------------------------------------------------
    # Bench Press
    # ------------------------------------------------

    if "bench press" in raw_input:

        parsed_metrics = {

            "exercise_detected":
                "Bench Press",

            "sets":
                4,

            "reps":
                8,

            "weight_kg":
                80.0
        }

        assessment = (
            "Keep shoulder blades retracted "
            "and maintain stable foot placement "
            "during pressing."
        )


    # ------------------------------------------------
    # Squat
    # ------------------------------------------------

    elif "squat" in raw_input:

        parsed_metrics = {

            "exercise_detected":
                "Squat",

            "sets":
                3,

            "reps":
                5,

            "weight_kg":
                100.0
        }

        assessment = (
            "Maintain a braced core and drive "
            "the knees in line with the toes. "
            "Avoid valgus collapse."
        )


    # ------------------------------------------------
    # Deadlift
    # ------------------------------------------------

    elif "deadlift" in raw_input:

        parsed_metrics = {

            "exercise_detected":
                "Deadlift",

            "sets":
                3,

            "reps":
                5,

            "weight_kg":
                120.0
        }

        assessment = (
            "Keep the bar close to the body, "
            "brace before initiating the pull, "
            "and maintain a neutral spine."
        )


    # ------------------------------------------------
    # Overhead Press
    # ------------------------------------------------

    elif (
        "overhead press" in raw_input
        or "ohp" in raw_input
    ):

        parsed_metrics = {

            "exercise_detected":
                "Overhead Press",

            "sets":
                3,

            "reps":
                8,

            "weight_kg":
                40.0
        }

        assessment = (
            "Brace the core and avoid excessive "
            "lower-back extension while pressing."
        )


    return {

        "parsed_workout_metrics":
            parsed_metrics,

        "physiological_assessment":
            assessment
    }


if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001
    )