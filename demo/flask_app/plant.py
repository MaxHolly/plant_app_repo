from flask import Blueprint, flash, g, redirect, render_template, request, url_for, current_app
from werkzeug.exceptions import abort
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta
import math
import pandas as pd

from flask_app.auth import login_required
from flask_app.models import db, Plant, UserPlant
from flask_app.models import User  # if user information is needed

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
    user_id = g.user.user_id  # Access the current user from the ORM model

    # Query the database using SQLAlchemy ORM instead of raw SQL
    plants = db.session.query(Plant, UserPlant).join(UserPlant).filter(UserPlant.user_id == user_id).all()

    # Convert the result into a Pandas DataFrame for manipulation
    plant_data = []
    for plant, userplant in plants:
        plant_data.append({
            'plant_id': plant.plant_id,
            'common_name': plant.common_name,
            'botanical_name': plant.botanical_name,
            'image_location': plant.image_location,
            'plant_type': plant.plant_type,
            'water_needs':plant.water_needs,
            'min_water_consumption':plant.min_water_consumption,
            'max_water_consumption':plant.max_water_consumption,
            'climate_zones':plant.climate_zones,
            'light_needs':plant.light_needs,
            'soil_type':plant.soil_type,
            'maintenance':plant.maintenance,
            'flower_color':plant.flower_color,
            'foliage_color':plant.foliage_color,
            'perfume':plant.perfume,
            'aromatic':plant.aromatic,
            'edible':plant.edible,
            'bore_water_tolerance':plant.bore_water_tolerance,
            'frost_tolerance':plant.frost_tolerance,
            'sun_exposure': userplant.sun_exposure,
            'size': userplant.size,
            'last_watered': userplant.last_watered,
            'pot_diameter': userplant.pot_diameter,
            'watered_amount': userplant.watered_amount,
            'plant_position': userplant.plant_position,
            'user_plant_id': userplant.user_plant_id,
            'min_water_consumption': plant.min_water_consumption,
            'max_water_consumption': plant.max_water_consumption,
            'plant_nickname': userplant.plant_nickname,
            'image_path': userplant.image_path
        })

    plants_df = pd.DataFrame(plant_data)
    notifications = []
    daily_water_consumption_list = []
    next_watering_date_list = []
    time_to_watering_list = []
    needs_watering_list = []

    if not plants_df.empty:
        for idx, plant in plants_df.iterrows():
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
                        'position': idx
                    })
                time_to_watering_list.append(time_to_watering)
                needs_watering_list.append(needs_watering)

        plants_df['daily_water_consumption'] = daily_water_consumption_list
        plants_df['next_watering_date'] = next_watering_date_list
        plants_df['time_to_watering'] = time_to_watering_list
        plants_df['needs_watering'] = needs_watering_list
        return plants_df, notifications
    else:
        return plants_df, notifications

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

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
        # Extract plant name from form
        plant_name = request.form['plant_name']
        # Query the database using SQLAlchemy ORM
        plants = Plant.query.filter(Plant.common_name.ilike(f"%{plant_name}%")).all()
        return render_template('plant/add.html', plants=plants)
    return render_template('plant/add.html', plants=[])


@bp.route('/select/<int:plant_id>', methods=['GET'])
@login_required
def select(plant_id):
    # Query using SQLAlchemy ORM
    selected_plant = Plant.query.get_or_404(plant_id)
    return render_template('plant/add.html', selected_plant=selected_plant)


@bp.route('/save', methods=['POST'])
@login_required
def save():
    if request.method == 'POST':
        user_id = g.user.user_id
        plant_id = request.form['selected_plant_id']
        size = request.form['size']
        sun_exposure = request.form['sun_exposure']
        last_watered_str = request.form['last_watered']
        pot_diameter = request.form['pot_diameter']
        watered_amount = request.form['watered_amount']
        plant_position = request.form['plant_position']
        plant_nickname = request.form['plant_nickname']

        last_watered = datetime.strptime(last_watered_str, '%Y-%m-%d')
        # Insert a new UserPlant using SQLAlchemy ORM
        user_plant = UserPlant(
            user_id=user_id,
            plant_id=plant_id,
            size=size,
            sun_exposure=sun_exposure,
            last_watered=last_watered,
            pot_diameter=pot_diameter,
            watered_amount=watered_amount,
            plant_position=plant_position,
            plant_nickname=plant_nickname
        )
        db.session.add(user_plant)
        db.session.commit()

        flash('Plant registered successfully!')
        return render_template('plant/save.html', user_plant_id=user_plant.user_plant_id)

    return redirect(url_for('plant.add'))


@bp.route('/<int:user_plant_id>/update', methods=('GET', 'POST'))
@login_required
def update(user_plant_id):
    """Update a user's plant."""
    # Get the UserPlant object using SQLAlchemy ORM
    user_plant = UserPlant.query.get_or_404(user_plant_id)
    plant = Plant.query.get_or_404(user_plant.plant_id)


    # Ensure the current user owns this plant
    if user_plant.user_id != g.user.user_id:
        abort(403)  # HTTP Forbidden

    if request.method == 'POST':
        # Get form data
        size = request.form.get('size')
        last_watered_str = request.form.get('last_watered')
        sun_exposure = request.form.get('sun_exposure')
        pot_diameter = request.form.get('pot_diameter')
        watered_amount = request.form.get('watered_amount')
        plant_position = request.form.get('plant_position')
        plant_nickname = request.form.get('plant_nickname')
        error = None

        # Handle file upload
        if 'image' in request.files and request.files['image'].filename != '':
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                relative_file_path = os.path.join('images', filename).replace('\\', '/')
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename).replace('\\', '/')
                try:
                    file.save(file_path)
                    user_plant.image_path = relative_file_path
                except Exception as e:
                    error = f"File upload failed: {str(e)}"
            else:
                error = 'Invalid file type or no file selected.'

        if error is not None:
            flash(error)
        else:
            # Update the user_plant object
            try:
                user_plant.size = float(size) if size else None
                user_plant.sun_exposure = sun_exposure
                if last_watered_str:
                    user_plant.last_watered = datetime.strptime(last_watered_str, '%Y-%m-%d')
                else:
                    user_plant.last_watered = None
                user_plant.pot_diameter = float(pot_diameter) if pot_diameter else None
                user_plant.watered_amount = float(watered_amount) if watered_amount else None
                user_plant.plant_position = plant_position
                user_plant.plant_nickname = plant_nickname
                # Save changes to the database
                db.session.commit()
                flash('Plant updated successfully!')
                return redirect(url_for('plant.index'))
            except ValueError as e:
                flash(f'Invalid input: {e}')
                # No need to redirect; the template will display the error

    # GET request or form validation failed
    return render_template('plant/update.html', user_plant=user_plant)

@bp.route('/user_plant_id/delete', methods=('POST',))
@login_required
def delete(user_plant_id):
    """Delete a user's plant."""
    # Get the UserPlant object using SQLAlchemy ORM
    user_plant = UserPlant.query.get_or_404(user_plant_id)

    # Ensure the current user owns this plant
    if user_plant.user_id != g.user.user_id:
        abort(403)  # HTTP Forbidden

    # Delete the user_plant
    db.session.delete(user_plant)
    db.session.commit()
    flash('Plant deleted successfully.')
    return redirect(url_for('plant.index'))

@bp.route('/<int:user_plant_id>/user_popup')
@login_required
def user_popup(user_plant_id):
    """
    Route for pop-up of showing general plant information when hovering over plant picture
    """
    page = request.args.get('page', 1, type=int)
    
    # Fetch the UserPlant and associated Plant
    user_plant = UserPlant.query.get_or_404(user_plant_id)
    plant = Plant.query.get_or_404(user_plant.plant_id)

    return render_template('plant/user_plant_popup.html', user_plant=user_plant, plant=plant, page=page)
