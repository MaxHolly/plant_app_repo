from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, current_app
)
from werkzeug.exceptions import abort
import bleach

from flask_app.auth import login_required
from flask_app.db import get_db

bp = Blueprint('user', __name__, url_prefix='/user')

@bp.route('/config')
def get_config():
    return {
        # 'SECRET_KEY': current_app.config['SECRET_KEY'],
        'PLANTS_PER_PAGE': current_app.config['PLANTS_PER_PAGE'],
        'DATABASE': current_app.config['DATABASE'],
        'UPLOAD_FOLDER': current_app.config['UPLOAD_FOLDER'],
        'ALLOWED_EXTENSIONS': current_app.config['ALLOWED_EXTENSIONS'],
        'MAX_CONTENT_LENGTH': current_app.config['MAX_CONTENT_LENGTH']
    }


def get_user(username):
    user_id = g.user['user_id']
    user = get_db().execute(
        """ SELECT u.user_id, u.username, u.email, u.avatar, u.last_time_seen, u.user_description,
                   COUNT(DISTINCT up.user_plant_id) as user_plant_count
        FROM User as u
        LEFT JOIN UserPlant as up ON u.user_id = up.user_id
        WHERE u.username = ?
        AND u.user_id = ?
        """,
        (username, user_id,)
    ).fetchone()

    if user is None:
        abort(404, f"User with id {user_id} and username {username} doesn't exist.")

    return user

@bp.route('/<username>', methods=('GET', 'POST'))
@login_required
def user(username):
    user = get_user(username)

    return render_template('user/user.html', user=user)


@bp.route('/<username>/edit_profile', methods=('GET', 'POST'))
@login_required
def edit_profile(username):
    user = get_user(username)

    if request.method == 'POST':
        username = request.form['username']
        user_description = bleach.clean(request.form['user_description'], strip=True)
        error = None

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE User SET username = ?, user_description = ? '
                ' WHERE user_id = ?',
                (username, user_description, user['user_id'])
            )
            db.commit()
            flash('Your changes have been saved.')
            return redirect(url_for('user.user', username=username))

    return render_template('user/edit_profile.html', user=user)