import functools
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms.validators import Email
from hashlib import md5
from datetime import datetime, timezone

from flask_app.models import db, User  # Import the User model

bp = Blueprint('auth', __name__, url_prefix='/auth')

# User registration
@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password2 = request.form['password2']
        email = request.form['email']
        error = None
        
        # md5-hashed email for gravatar service
        digest = md5(email.lower().encode('utf-8')).hexdigest()
        avatar_link = f'https://www.gravatar.com/avatar/{digest}?d=identicon&s=128'

        # Validation
        if not username:
            error = 'Username is required.'
        elif not email:
            error = 'Email is required.'
        elif not password:
            error = 'Password is required.'
        elif not password2:
            error = 'Repeating password is required.'
        elif password != password2:
            error = 'Given passwords are not the same!'

        # Check if there are no validation errors
        if error is None:
            try:
                # Create a new user instance
                new_user = User(
                    username=username,
                    email=email,
                    avatar=avatar_link,
                    password=generate_password_hash(password),
                    last_time_seen=datetime.now(timezone.utc)  # Initialize last seen to current time
                )
                db.session.add(new_user)
                db.session.commit()  # Commit the transaction to save the user in the database
            except Exception:
                error = f"User {username} is already registered."
            else:
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template('auth/register.html')

# User login
@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        error = None
        
        # Fetch the user from the database
        user = User.query.filter_by(username=username).first()

        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user.password, password):
            error = 'Incorrect password.'

        if error is None:
            # Log in the user by clearing session and setting the user_id in session
            session.clear()
            session['user_id'] = user.user_id
            return redirect(url_for('index'))

        flash(error)

    return render_template('auth/login.html')

# Before every request, load the logged-in user from the session
@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        # Fetch the user using the user_id stored in session
        g.user = User.query.get(user_id)
        
        if g.user:
            # Update the last_time_seen field
            g.user.last_time_seen = datetime.now(timezone.utc)
            db.session.commit()

# Logout
@bp.route('/logout')
def logout():
    session.clear()  # Clear the session to log out the user
    return redirect(url_for('index'))

# Login required decorator
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))
        return view(**kwargs)
    return wrapped_view
