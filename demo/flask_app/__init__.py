import os

from flask import Flask, g
from . import config

from .plant import get_plant_and_notifications


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)

    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_object('flask_app.config.Config')
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    
    from . import db
    db.init_app(app)

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


    return app