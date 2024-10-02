# flask_app/__init__.py
import os
from flask import Flask, g
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from .models import db
from .plant import get_plant_and_notifications

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_object('flask_app.config.Config')

    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    # Database configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(app.instance_path, 'app.sqlite')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)

    # Register blueprints
    from . import auth
    app.register_blueprint(auth.bp)

    from . import user
    app.register_blueprint(user.bp)

    from . import plant
    app.register_blueprint(plant.bp)
    app.add_url_rule('/', endpoint='index')

    @app.context_processor
    def inject_notifications():
        if g.user:
            plants, notifications = get_plant_and_notifications()
            per_page = app.config['PLANTS_PER_PAGE']
            return dict(notifications=notifications, notification_count=len(notifications), per_page=per_page)
        return dict(notifications=[], notification_count=0)

    # Import custom CLI commands
    from flask_app.commands import import_plants_command, update_plants_command  # Use absolute import
    app.cli.add_command(import_plants_command)
    app.cli.add_command(update_plants_command)

    return app
