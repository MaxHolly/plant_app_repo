from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from flask_app.auth import login_required
from flask_app.db import get_db

bp = Blueprint('plant', __name__)

@bp.route('/')
@login_required
def index():
    """Show all plants registered by the current user."""
    db = get_db()
    user_id = g.user['user_id']
    plants = db.execute(
        """SELECT p.*,
                  up.* 
        FROM Plant p 
        JOIN UserPlant up ON p.plant_id = up.plant_id 
        WHERE up.user_id = ?
        ORDER BY up.registered_at DESC""",
        (user_id,)
    ).fetchall()
    return render_template('plant/index.html', plants=plants)

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

        db = get_db()
        db.execute(
            "INSERT INTO UserPlant (user_id, plant_id, size, sun_exposure, last_watered) VALUES (?, ?, ?, ?, ?)",
            (user_id, plant_id, size, sun_exposure, last_watered)
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
        error = None

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE UserPlant SET size = ?, last_watered = ?, sun_exposure = ?'
                ' WHERE user_plant_id = ?',
                (size, last_watered, sun_exposure, user_plant_id)
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
