import sqlite3
import csv

import click
import os
from flask import current_app, g


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()

def init_db():
    db = get_db()
    csv_file_path = os.path.join(current_app.root_path, 'data', 'waterwise_plants_cleaned.csv')


    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))
    
    # Read data from CSV file and insert into Plant table
    with open(csv_file_path, newline='') as csvfile:
        csvreader = csv.DictReader(csvfile)
        for row in csvreader:
            db.execute(
                """INSERT INTO Plant (
                    plant_id, botanical_name, common_name, plant_type, water_needs, min_water_consumption, max_water_consumption,
                    climate_zones, light_needs, soil_type, maintenance, flower_color, foliage_color , perfume, aromatic, edible, bore_water_tolerance, frost_tolerance, image_location
                    ) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (row['Plant ID'], row['Botanical Name'], row['Common Name'], row['Plant Type'], row['Water Needs'], row['min_water_consumption'], row['max_water_consumption'],
                  row['Climate Zones'], row['Light Needs'], row['Soil Type'], row['Maintenance'], row['Flower colour'], row['Foliage Colour'], row['Perfume'], row['Aromatic'], row['Edible'], row['Bore water Tolerance'], row['Frost Tolerance'], row['Image Location'])
            )
        db.commit()



@click.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')

    
def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)