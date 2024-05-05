import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms.validators import Email

from flask_app.db import get_db
from hashlib import md5

from datetime import datetime, timezone

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password2 = request.form['password2']
        email = request.form['email']
        db = get_db()
        error = None
        
        # md5-hashed e-mail for gravatar service
        digest = md5(email.lower().encode('utf-8')).hexdigest()
        avatar_link = f'https://www.gravatar.com/avatar/{digest}?d=identicon&s=128'

        if not username:
            error = 'Username is required.'
        elif not email:
            error = 'Email is required.'
        elif not password:
            error = 'Password is required.'
        elif not password2:
            error = 'Repeating password is required.'
        elif password!=password2:
            error = 'Given passwords are not the same!'

        if error is None:
            try:
                db.execute(
                    "INSERT INTO user (username, email, avatar, password) VALUES (?, ?, ?, ?)",
                    (username, email, avatar_link,generate_password_hash(password)),
                )
                db.commit()
            except db.IntegrityError:
                error = f"User {username} is already registered."
            else:
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template('auth/register.html')

@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM user WHERE username = ?', (username,)
        ).fetchone()

        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'

        if error is None:
            session.clear()
            session['user_id'] = user['user_id']
            return redirect(url_for('index'))

        flash(error)

    return render_template('auth/login.html')

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        db = get_db()
        g.user = db.execute(
            'SELECT * FROM user WHERE user_id = ?', (user_id,)
        ).fetchone()
        last_time_seen = datetime.now(timezone.utc)
        db.execute(
                'UPDATE User SET last_time_seen = ?'
                ' WHERE user_id = ?',
                (last_time_seen, user_id, )
            )
        db.commit()
        

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view