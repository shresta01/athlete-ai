# Runbook: Algorithmic Dietary Consultation & Macro Tracking
Signatures: "diet", "nutrition", "calories", "macros", "protein", "carbs", "fat", "bulking", "cutting", "mass", "lose", "weight", "kg", "lbs"

## 1. Dynamic Caloric Strategy Equations
To calculate an athlete's total daily target, first extract their current weight in kilograms ($W$). If the user provides weight in pounds, convert it first ($W_{\text{kg}} = W_{\text{lbs}} \div 2.2$).

### Baseline Maintenance Intake Calculation
*   Estimated Maintenance Calories = $W_{\text{kg}} \times 33$ (Use as the fundamental baseline balance point).

### Operational Phase Tracking
*   **Bulking Goal (Muscle Gain Phase):** Target a surplus. Add 300 to 500 calories directly onto the Baseline Maintenance total. This provides the energy required to support muscle tissue hypertrophy while minimizing excess fat gain.
*   **Cutting Goal (Fat Loss Phase):** Target a deficit. Subtract 400 to 600 calories directly from the Baseline Maintenance total. This forces the body to mobilize stored adipose tissue for energy.

## 2. Precise Structural Macronutrient Distribution Rules
Once the total daily caloric target is established based on the training phase above, calculate macro splits using these priority steps:

1.  **Protein Target (The Foundation):**
    *   *If Bulking:* Allocate $2.0\text{g}$ of protein per kilogram of body weight ($2.0 \times W_{\text{kg}}$).
    *   *If Cutting:* Allocate $2.4\text{g}$ of protein per kilogram of body weight ($2.4 \times W_{\text{kg}}$) to preserve lean muscle tissue during a caloric deficit.
    *   *(Note: 1 gram of protein = 4 calories)*

2.  **Fat Target (Hormonal Regulation Baseline):**
    *   Allocate roughly $20\%$ to $25\%$ of the total daily caloric target to healthy fats.
    *   *(Note: 1 gram of fat = 9 calories)*

3.  **Carbohydrate Target (Performance Fueling Balance):**
    *   All remaining daily calories are assigned to carbohydrates to optimize glycogen storage and fuel hard workouts.
    *   *(Note: 1 gram of carbohydrate = 4 calories)*