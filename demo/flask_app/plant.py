from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from flask_app.auth import login_required
from flask_app.db import get_db

from datetime import datetime, timedelta
import math
import pandas as pd

bp = Blueprint('plant', __name__)

def calculate_water_consumption(sun_exposure, pot_diameter, min_water, max_water):
    if sun_exposure == 'low':
        daily_consumption_mm = min_water / 365
    elif sun_exposure == 'medium':
        daily_consumption_mm = (min_water + max_water) / 2 / 365
    else:  # high sun exposure
        daily_consumption_mm = max_water / 365

    # Area of the pot in square meters
    pot_area = math.pi * (pot_diameter / 100 / 2) ** 2  # converting diameter to meters

    # Daily water consumption in liters
    daily_consumption_l = daily_consumption_mm * pot_area

    return daily_consumption_l

def calculate_next_watering(watered_date, watered_amount, daily_consumption):
    days_to_next_watering = watered_amount / daily_consumption
    next_watering_date = pd.to_datetime(watered_date) + timedelta(days=days_to_next_watering)
    return next_watering_date

@bp.route('/')
@login_required
def index():
    """Show all plants registered by the current user."""
    db = get_db()
    user_id = g.user['user_id']
    plant_cursor = db.execute(
        """SELECT p.*,
                  up.* 
        FROM Plant p 
        JOIN UserPlant up ON p.plant_id = up.plant_id 
        WHERE up.user_id = ?
        ORDER BY up.registered_at DESC""",
        (user_id,)
    )
    cols = [description[0] for description in plant_cursor.description]
    plants= pd.DataFrame.from_records(data = plant_cursor.fetchall(), columns = cols)

    if plants.shape[0] != 0:
    # if result dataframe contains any rows then performa calculations
    # calculate daily water consumption and next watering date for each plant in returned list
        daily_water_consumption_plant = []
        for index, row in plants.iterrows():
            daily_water_consumption_plant.append(
                calculate_water_consumption(sun_exposure=row['sun_exposure'],
                                            pot_diameter=row['pot_diameter'],
                                            min_water=row['min_water_consumption'],
                                            max_water=row['max_water_consumption'])
                                            )

        plants['daily_water_consumption'] = daily_water_consumption_plant

        next_watering_date = []
        for index, row in plants.iterrows():
            next_watering_date.append(
                calculate_next_watering(watered_date=row['last_watered'],
                                        watered_amount=row['watered_amount'],
                                        daily_consumption=row['daily_water_consumption']
                                        )
                                        )
        plants['next_watering_date'] = next_watering_date

    else: # if no rows in result set, return empty list
        pass
    
    # convert to list of named tuples so that jinja for loop can list plants in index.html
    plants_list = list(plants.itertuples(index=False))
    return render_template('plant/index.html', plants=plants_list)

@bp.route('/add', methods=('GET', 'POST'))
@login_required
def add():
    """Add a new plant to the user's account."""
    if request.method == 'POST':
        # Handle form submission
        # Extract plant name from form
        plant_name = request.form['plant_name']
        # Query the database to find matching plants
        db = get_db()
        plants = db.execute(
            "SELECT * FROM Plant WHERE common_name LIKE ?",
            ('%' + plant_name + '%',)
        ).fetchall()
        return render_template('plant/add.html', plants=plants)
    return render_template('plant/add.html', plants=[])

@bp.route('/select/<int:plant_id>', methods=['GET'])
@login_required
def select(plant_id):
    db = get_db()
    selected_plant = db.execute(
        "SELECT * FROM Plant WHERE plant_id = ?",
        (plant_id,)
    ).fetchone()
    if not selected_plant:
        abort(404, "Plant id {0} doesn't exist.".format(plant_id))
    return render_template('plant/add.html', selected_plant=selected_plant)

@bp.route('/save', methods=['POST'])
@login_required
def save():
    if request.method == 'POST':
        user_id = g.user['user_id']
        plant_id = request.form['selected_plant_id']
        size = request.form['size']
        sun_exposure = request.form['sun_exposure']
        last_watered = request.form['last_watered']
        pot_diameter = request.form['pot_diameter']
        watered_amount = request.form['watered_amount']

        db = get_db()
        db.execute(
            "INSERT INTO UserPlant (user_id, plant_id, size, sun_exposure, last_watered, pot_diameter, watered_amount) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, plant_id, size, sun_exposure, last_watered, pot_diameter, watered_amount)
        )
        db.commit()
        flash('Plant registered successfully!')

        return render_template('plant/save.html')
    
    return redirect(url_for('plant.add'))

def get_added_plant(plant_id, check_owner=True):
    user_id = g.user['user_id']
    added_plant = get_db().execute(
        """SELECT up.user_plant_id, up.user_id, up.plant_id, p.common_name
        FROM User u JOIN UserPlant up ON u.user_id = up.user_id
        JOIN Plant p ON up.plant_id = p.plant_id
        WHERE up.plant_id = ?
        AND u.user_id = ?""",
        (plant_id, user_id)
    ).fetchone()

    if added_plant is None:
        abort(404, f"Plant with id {added_plant['plant_id']} doesn't exist for user {g.user['user_id']}.")

    if check_owner and added_plant['user_id'] != g.user['user_id']:
        abort(403)

    return added_plant

@bp.route('/<int:plant_id>/update', methods=('GET', 'POST'))
@login_required
def update(plant_id):
    user_plant = get_added_plant(plant_id)

    if request.method == 'POST':
        user_plant_id = user_plant['user_plant_id']
        size = request.form['size']
        last_watered = request.form['last_watered']
        sun_exposure = request.form['sun_exposure']
        pot_diameter = request.form['pot_diameter']
        watered_amount = request.form['watered_amount']
        error = None

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE UserPlant SET size = ?, last_watered = ?, sun_exposure = ?, pot_diameter = ?, watered_amount = ?'
                ' WHERE user_plant_id = ?',
                (size, last_watered, sun_exposure, pot_diameter, watered_amount, user_plant_id)
            )
            db.commit()
            return redirect(url_for('plant.index'))

    return render_template('plant/update.html', user_plant=user_plant)

@bp.route('/<int:plant_id>/delete', methods=('POST',))
@login_required
def delete(plant_id):
    user_plant = get_added_plant(plant_id)
    user_plant_id = user_plant['user_plant_id']
    
    db = get_db()
    db.execute('DELETE FROM UserPlant WHERE user_plant_id = ?', (user_plant_id,))
    db.commit()
    return redirect(url_for('plant.index'))
