from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort
import bleach

from flask_app.auth import login_required
from flask_app.models import db, User, UserPlant

bp = Blueprint('user', __name__, url_prefix='/user')

# Helper function to fetch user and associated plant count
def get_user(username):
    user_id = g.user.user_id
    user = db.session.query(User).filter_by(user_id=user_id, username=username).first()

    if user is None:
        abort(404, f"User with id {user_id} and username {username} doesn't exist.")

    # Query to count the number of plants associated with the user
    user_plant_count = db.session.query(UserPlant).filter_by(user_id=user.user_id).count()

    # Adding the plant count to the user object (or you could pass this as separate context to the template)
    user.user_plant_count = user_plant_count

    return user


# Route to view user profile
@bp.route('/<username>', methods=('GET', 'POST'))
@login_required
def user(username):
    user = get_user(username)
    return render_template('user/user.html', user=user)


# Route to edit user profile
@bp.route('/<username>/edit_profile', methods=('GET', 'POST'))
@login_required
def edit_profile(username):
    user = get_user(username)

    if request.method == 'POST':
        new_username = request.form['username']
        user_description = bleach.clean(request.form['user_description'], strip=True)
        error = None

        # Add validation checks if needed (e.g., username uniqueness)

        if error is not None:
            flash(error)
        else:
            # Update user information using SQLAlchemy ORM
            user.username = new_username
            user.user_description = user_description
            db.session.commit()  # Commit the changes to the database
            flash('Your changes have been saved.')
            return redirect(url_for('user.user', username=user.username))

    return render_template('user/edit_profile.html', user=user)
