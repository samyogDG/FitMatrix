from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import pickle
import hashlib

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure secret key

# Load the datasets
meal_file_path = 'Data_Sets/filtered_data.csv'
meal_data = pd.read_csv(meal_file_path)

exercise_file_path = 'Data_Sets/filtered_data2.csv'
exercise_data = pd.read_csv(exercise_file_path)

# Load the workout recommendation model
model_path = 'ML_Models/workout_recommendation_model.pkl'
with open(model_path, 'rb') as model_file:
    workout_model = pickle.load(model_file)

# In-memory user store (use a database for production)
users = {}

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Define a decorator to check if user is logged in
def login_required(f):
    def wrap(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

# Define routes
@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        age = int(request.form.get('age'))
        gender = request.form.get('gender')
        weight = float(request.form.get('weight'))
        height = float(request.form.get('height'))
        vegetarian = request.form.get('vegetarian') == 'on'

        bmi = weight / ((height / 100) ** 2)
        bmi_status = get_bmi_status(bmi)

        bmr = calculate_bmr(weight, height, age, gender)
        maintain_weight = bmr
        mild_weight_loss = bmr - 500 * 0.25
        weight_loss = bmr - 500 * 0.5
        extreme_weight_loss = bmr - 500 * 1

        protein_intake = weight * 1.6

        preferences = {
            "vegetarian": vegetarian,
            "calorie_limit": maintain_weight,
            "protein_limit": protein_intake
        }

        filtered_meal_data = filter_data(meal_data, preferences)
        meal_plan = generate_meal_plan(filtered_meal_data, preferences)

        top_exercises = get_top_exercises(exercise_data)

        return render_template('result.html', bmi=bmi, bmi_status=bmi_status,
                               maintain_weight=maintain_weight, mild_weight_loss=mild_weight_loss,
                               weight_loss=weight_loss, extreme_weight_loss=extreme_weight_loss,
                               protein_intake=protein_intake, meal_plan=meal_plan,
                               top_exercises=top_exercises)

    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username in users:
            return 'User already exists!'

        users[username] = hash_password(password)
        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    message = None  # Initialize message variable

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        hashed_password = hash_password(password)
        if users.get(username) == hashed_password:
            session['username'] = username
            return redirect(url_for('index'))

        message = 'Invalid credentials!'  # Show this message if credentials are wrong

    return render_template('login.html', message=message)


@app.route('/logout')
@login_required
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/all-exercises')
@login_required
def all_exercises():
    top_exercises = get_top_exercises(exercise_data)
    return render_template('all_exercises.html', top_exercises=top_exercises)

def get_bmi_status(bmi):
    if bmi < 18.5:
        return "Underweight"
    elif 18.5 <= bmi < 24.9:
        return "Normal weight"
    elif 25 <= bmi < 29.9:
        return "Overweight"
    else:
        return "Obesity"

def calculate_bmr(weight, height, age, gender):
    if gender == 'male':
        return 10 * weight + 6.25 * height - 5 * age + 5
    else:
        return 10 * weight + 6.25 * height - 5 * age - 161

def filter_data(data, preferences):
    filtered_data = data.copy()
    if preferences["vegetarian"]:
        filtered_data = filtered_data[filtered_data["VegNovVeg"] == 1]
    return filtered_data

def generate_meal_plan(filtered_data, preferences):
    breakfast_calories = preferences["calorie_limit"] * 0.3
    lunch_calories = preferences["calorie_limit"] * 0.4
    dinner_calories = preferences["calorie_limit"] * 0.3

    breakfast_protein = preferences["protein_limit"] * 0.3
    lunch_protein = preferences["protein_limit"] * 0.4
    dinner_protein = preferences["protein_limit"] * 0.3

    breakfast_options = filtered_data[filtered_data["Breakfast"] == 1]
    lunch_options = filtered_data[filtered_data["Lunch"] == 1]
    dinner_options = filtered_data[filtered_data["Dinner"] == 1]

    meal_plan = {
        "Breakfast": [],
        "Lunch": [],
        "Dinner": []
    }

    def select_random_meals(meal_options, calorie_limit, protein_limit):
        shuffled_options = meal_options.sample(frac=1).reset_index(drop=True)

        total_calories = 0
        total_protein = 0

        selected_meals = []

        for _, row in shuffled_options.iterrows():
            if total_calories + row["Calories"] <= calorie_limit and total_protein + row["Proteins"] <= protein_limit:
                selected_meals.append({
                    "Food_items": row["Food_items"],
                    "Calories": row["Calories"],
                    "Fats": row["Fats"],
                    "Proteins": row["Proteins"],
                    "Iron": row["Iron"],
                    "Calcium": row["Calcium"],
                    "Sodium": row["Sodium"],
                    "Potassium": row["Potassium"],
                    "Carbohydrates": row["Carbohydrates"],
                    "Fibre": row["Fibre"],
                    "VitaminD": row["VitaminD"],
                    "Sugars": row["Sugars"]
                })
                total_calories += row["Calories"]
                total_protein += row["Proteins"]

            if total_calories >= calorie_limit and total_protein >= protein_limit:
                break

        return selected_meals

    meal_plan["Breakfast"] = select_random_meals(breakfast_options, breakfast_calories, breakfast_protein)
    meal_plan["Lunch"] = select_random_meals(lunch_options, lunch_calories, lunch_protein)
    meal_plan["Dinner"] = select_random_meals(dinner_options, dinner_calories, dinner_protein)

    return meal_plan

def get_top_exercises(exercise_data):
    body_parts = exercise_data['BodyPart'].unique()
    top_exercises = {}

    for part in body_parts:
        top_exercises[part] = exercise_data[exercise_data['BodyPart'] == part].nlargest(5, 'Rating')

    return top_exercises

if __name__ == '__main__':
    app.run(debug=True)
