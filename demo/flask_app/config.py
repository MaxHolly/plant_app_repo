import os

class Config:
    SECRET_KEY='dev'
    PLANTS_PER_PAGE = 3
    DATABASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'instance', 'plant_app_db.sqlite')
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/images')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

# Ensure the upload folder exists
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)