import pandas as pd
from typing import List, Dict
from src.state import FitnessPlan, NutritionPlan, ProgressUpdate
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
import os

def export_plans_to_excel(fitness_plan: FitnessPlan, nutrition_plan: NutritionPlan, filepath: str = "Client_Plan.xlsx"):
    """
    Exports the verified fitness and nutrition plans to a beautifully formatted multi-sheet Excel file.
    """
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        # Sheet 1: Weekly Workout Schedule
        workout_data = []
        for domain, sessions in [("Gym", fitness_plan.gym_sessions), 
                                 ("Yoga", fitness_plan.yoga_sessions), 
                                 ("Calisthenics", fitness_plan.calisthenics_sessions)]:
            for session in sessions:
                for ex in session.exercises:
                    workout_data.append({
                        "Domain": domain,
                        "Day": session.day,
                        "Focus": session.focus,
                        "Duration (mins)": session.duration_mins,
                        "Exercise": ex.get("name", str(ex)),
                        "Sets/Reps": ex.get("sets_reps", "")
                    })
        
        if workout_data:
            df_workout = pd.DataFrame(workout_data)
        else:
            df_workout = pd.DataFrame(columns=["Domain", "Day", "Focus", "Duration (mins)", "Exercise", "Sets/Reps"])
            
        df_workout.to_excel(writer, sheet_name="Weekly Workout Schedule", index=False)
        
        # Sheet 2: Daily Macro & Meal Plan
        meal_data = []
        if nutrition_plan and nutrition_plan.daily_meals:
            for meal in nutrition_plan.daily_meals:
                meal_data.append({
                    "Meal": meal.meal_name,
                    "Description": meal.description,
                    "Calories": meal.calories,
                    "Protein (g)": meal.protein_g,
                    "Carbs (g)": meal.carbs_g,
                    "Fats (g)": meal.fats_g
                })
        
        if meal_data:
            df_meals = pd.DataFrame(meal_data)
        else:
            df_meals = pd.DataFrame(columns=["Meal", "Description", "Calories", "Protein (g)", "Carbs (g)", "Fats (g)"])
            
        df_meals.to_excel(writer, sheet_name="Daily Macro & Meal Plan", index=False)
        
        # Sheet 3: Tracker Template
        df_tracker = pd.DataFrame(columns=["Date", "Weight (kg)", "Adherence Score (1-10)", "Notes"])
        df_tracker.to_excel(writer, sheet_name="Tracker Template", index=False)
        
    # Apply some basic formatting using openpyxl
    wb = writer.book
    header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            
        # Adjust column widths
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter # Get the column name
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2)
            ws.column_dimensions[column].width = adjusted_width

    wb.save(filepath)
    return filepath

def ingest_progress_tracker(filepath: str) -> List[ProgressUpdate]:
    """
    Parses an uploaded progress tracker Excel file into ProgressUpdate state objects.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Progress file not found: {filepath}")
        
    df = pd.read_excel(filepath, sheet_name="Tracker Template")
    
    updates = []
    for _, row in df.iterrows():
        if pd.notna(row.get("Date")) and pd.notna(row.get("Weight (kg)")):
            update = ProgressUpdate(
                date=str(row["Date"]),
                weight_kg=float(row["Weight (kg)"]),
                adherence_score=int(row.get("Adherence Score (1-10)", 5)),
                notes=str(row.get("Notes", ""))
            )
            updates.append(update)
            
    return updates
