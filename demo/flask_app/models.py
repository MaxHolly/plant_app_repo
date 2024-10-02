# flask_app/models.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Text, unique=True, nullable=False)
    email = db.Column(db.Text, nullable=False)
    avatar = db.Column(db.Text, nullable=False)
    password = db.Column(db.Text, nullable=False)
    user_description = db.Column(db.Text)
    last_time_seen = db.Column(db.TIMESTAMP)

    user_plants = db.relationship('UserPlant', back_populates='user')

class Plant(db.Model):
    __tablename__ = 'plant'
    plant_id = db.Column(db.Integer, primary_key=True)
    botanical_name = db.Column(db.Text)
    common_name = db.Column(db.Text)
    plant_type = db.Column(db.Text)
    water_needs = db.Column(db.Text)
    min_water_consumption = db.Column(db.Integer)
    max_water_consumption = db.Column(db.Integer)
    climate_zones = db.Column(db.Text)
    light_needs = db.Column(db.Text)
    soil_type = db.Column(db.Text)
    maintenance = db.Column(db.Text)
    flower_color = db.Column(db.Text)
    foliage_color = db.Column(db.Text)
    perfume = db.Column(db.Text)
    aromatic = db.Column(db.Text)
    edible = db.Column(db.Text)
    bore_water_tolerance = db.Column(db.Text)
    frost_tolerance = db.Column(db.Text)
    image_location = db.Column(db.Text)

    user_plants = db.relationship('UserPlant', back_populates='plant')



class UserPlant(db.Model):
    __tablename__ = 'userplant'
    user_plant_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))
    plant_id = db.Column(db.Integer, db.ForeignKey('plant.plant_id'))
    size = db.Column(db.Float)
    sun_exposure = db.Column(db.Text)
    last_watered = db.Column(db.DateTime)
    pot_diameter = db.Column(db.Float)
    watered_amount = db.Column(db.Float)
    image_path = db.Column(db.Text)
    plant_position = db.Column(db.Text)
    plant_nickname = db.Column(db.Text)
    registered_at = db.Column(db.TIMESTAMP, nullable=False, server_default=db.func.current_timestamp())

    user = db.relationship('User', back_populates='user_plants')
    plant = db.relationship('Plant', back_populates='user_plants')
