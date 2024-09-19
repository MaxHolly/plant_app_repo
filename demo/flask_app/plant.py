from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, current_app
)
from werkzeug.exceptions import abort
from werkzeug.utils import secure_filename
import os


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
    return next_watering_date.date()

def check_if_watering_needed(next_watering_date):
    today = datetime.today().date()
    time_to_watering_plant = today - next_watering_date
    # convert into int
    time_to_watering_plant = int(time_to_watering_plant / timedelta(days=1))
    if time_to_watering_plant >= 0:
        return (time_to_watering_plant, True)
    else:
        return (time_to_watering_plant, False)

def get_plant_and_notifications():
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
    plants = pd.DataFrame.from_records(data=plant_cursor.fetchall(), columns=cols)

    notifications = []
    daily_water_consumption_list = []
    next_watering_date_list = []
    time_to_watering_list = []
    needs_watering_list = []
    if plants.shape[0] != 0:

        for idx, plant in plants.iterrows():
            plant['daily_water_consumption'] = calculate_water_consumption(
                sun_exposure=plant['sun_exposure'],
                pot_diameter=plant['pot_diameter'],
                min_water=plant['min_water_consumption'],
                max_water=plant['max_water_consumption']
            )
            daily_water_consumption_list.append(plant['daily_water_consumption'])

            plant['next_watering_date'] = calculate_next_watering(
                watered_date=plant['last_watered'],
                watered_amount=plant['watered_amount'],
                daily_consumption=plant['daily_water_consumption']
            )
            next_watering_date_list.append(plant['next_watering_date'])

            if plant['next_watering_date']:
                time_to_watering, needs_watering = check_if_watering_needed(plant['next_watering_date'])
                plant['time_to_watering'] = time_to_watering
                plant['needs_watering'] = needs_watering
                if needs_watering:
                    overdue_days = time_to_watering if time_to_watering > 0 else 0
                    notifications.append({
                        'user_plant_id': plant['user_plant_id'],
                        'plant_name': plant['common_name'],
                        'overdue_days': overdue_days,
                        'position': idx  # Add position here
                    })
                time_to_watering_list.append(time_to_watering)
                needs_watering_list.append(needs_watering)

        plants['daily_water_consumption'] = daily_water_consumption_list
        plants['next_watering_date'] = next_watering_date_list
        plants['time_to_watering'] = time_to_watering_list
        plants['needs_watering'] = needs_watering_list
        return plants, notifications

    else:
        return plants, notifications


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@bp.route('/')
@login_required
def index():
    """Show all plants registered by the current user."""
    
    plants, notifications = get_plant_and_notifications()

    # add pagination
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['PLANTS_PER_PAGE']
    
    start = (page - 1) * per_page
    end = start + per_page
    paginated_plants = plants.iloc[start:end]


    # convert to list of named tuples so that jinja for loop can list plants in index.html
    plants_list = list(paginated_plants.itertuples(index=False))

    total_plants = len(plants)
    total_pages = (total_plants + per_page - 1) // per_page

    return render_template(
        'plant/index.html', 
        plants=plants_list, 
        notifications=notifications, 
        notification_count=len(notifications), 
        page=page, 
        total_pages=total_pages,
        per_page=per_page
    )


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
        plant_position = request.form['plant_position']
        plant_nickname = request.form['plant_nickname']

        db = get_db()
        cursor = db.execute(
            "INSERT INTO UserPlant (user_id, plant_id, size, sun_exposure, last_watered, pot_diameter, watered_amount, plant_position, plant_nickname) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, plant_id, size, sun_exposure, last_watered, pot_diameter, watered_amount, plant_position, plant_nickname)
        )
        db.commit()
        user_plant_id = cursor.lastrowid  # Get the last inserted row ID
        flash('Plant registered successfully!')

        return render_template('plant/save.html', user_plant_id = user_plant_id)
    
    return redirect(url_for('plant.add'))

def get_added_plant(user_plant_id, check_owner=True):
    user_id = g.user['user_id']
    added_plant = get_db().execute(
        """SELECT 
            up.user_plant_id, 
            up.user_id, 
            up.plant_id, 
            p.common_name, 
            up.sun_exposure,
            up.size,
            up.last_watered,
            up.pot_diameter,
            up.watered_amount,
            up.plant_position, 
            up.plant_nickname
        FROM User u JOIN UserPlant up ON u.user_id = up.user_id
        JOIN Plant p ON up.plant_id = p.plant_id
        WHERE up.user_plant_id = ?
        AND u.user_id = ?""",
        (user_plant_id, user_id)
    ).fetchone()

    if added_plant is None:
        abort(404, f"Plant with id {user_plant_id} doesn't exist for user {g.user['user_id']}.")

    if check_owner and added_plant['user_id'] != g.user['user_id']:
        abort(403)

    return added_plant



@bp.route('/<int:user_plant_id>/update', methods=('GET', 'POST'))
@login_required
def update(user_plant_id):
    user_plant = get_added_plant(user_plant_id)

    if request.method == 'POST':
        size = request.form['size']
        last_watered = request.form['last_watered']
        sun_exposure = request.form['sun_exposure']
        pot_diameter = request.form['pot_diameter']
        watered_amount = request.form['watered_amount']
        plant_position = request.form['plant_position']
        plant_nickname = request.form['plant_nickname']
        error = None

        # Handle file upload
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                relative_file_path = os.path.join('images', filename).replace('\\', '/')
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename).replace('\\', '/')
                try:
                    file.save(file_path)
                except Exception as e:
                    error = f"File upload failed: {str(e)}"
            else:
                relative_file_path = user_plant['image_path'] if 'image_path' in user_plant else None
        else:
            relative_file_path = user_plant['image_path'] if 'image_path' in user_plant else None

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE UserPlant SET size = ?, last_watered = ?, sun_exposure = ?, pot_diameter = ?, watered_amount = ?,  image_path = ?, plant_position = ?, plant_nickname = ?'
                ' WHERE user_plant_id = ?',
                (size, last_watered, sun_exposure, pot_diameter, watered_amount, relative_file_path, plant_position, plant_nickname, user_plant_id)
            )
            db.commit()
            return redirect(url_for('plant.index'))

    # Re-fetch the user_plant from the database to ensure it's up-to-date
    user_plant = get_added_plant(user_plant_id)
    return render_template('plant/update.html', user_plant=user_plant)


@bp.route('/<int:user_plant_id>/delete', methods=('POST',))
@login_required
def delete(plant_id):
    user_plant = get_added_plant(user_plant_id)
    user_plant_id = user_plant['user_plant_id']
    
    db = get_db()
    db.execute('DELETE FROM UserPlant WHERE user_plant_id = ?', (user_plant_id,))
    db.commit()
    return redirect(url_for('plant.index'))
