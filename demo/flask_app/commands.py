# flask_app/commands.py
import click
import csv
import os
from flask.cli import with_appcontext
from .models import db, Plant

@click.command('import-plants')
@with_appcontext
def import_plants_command():
    """Import plant data from CSV."""
    csv_file_path = os.path.join(os.path.dirname(__file__), 'data', 'waterwise_plants_cleaned.csv')

    with open(csv_file_path, newline='') as csvfile:
        csvreader = csv.DictReader(csvfile)
        for row in csvreader:
            plant = Plant(
                plant_id=int(float(row['Plant ID'])),
                botanical_name=row['Botanical Name'],
                common_name=row['Common Name'],
                plant_type=row['Plant Type'],
                water_needs=row['Water Needs'],
                min_water_consumption=int(float(row.get('min_water_consumption') or 0)),
                max_water_consumption=int(float(row.get('max_water_consumption') or 0)),
                climate_zones=row['Climate Zones'],
                light_needs=row['Light Needs'],
                soil_type=row['Soil Type'],
                maintenance=row['Maintenance'],
                flower_color=row['Flower colour'],
                foliage_color=row['Foliage Colour'],
                perfume=row['Perfume'],
                aromatic=row['Aromatic'],
                edible=row['Edible'],
                bore_water_tolerance=row['Bore water Tolerance'],
                frost_tolerance=row['Frost Tolerance'],
                image_location=row['Image Location']
            )
            db.session.add(plant)
        db.session.commit()
    click.echo('Imported plant data from CSV.')


@click.command('update-plants')
@with_appcontext
def update_plants_command():
    """Update existing Plant records with new image_location values from a CSV file."""
    # Path to your CSV file
    csv_file_path = os.path.join(os.path.dirname(__file__), 'data', 'waterwise_plants_cleaned.csv')

    with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
        plant_reader = csv.DictReader(csvfile)
        updated_records = 0
        skipped_records = 0
        for row in plant_reader:
            # Use a unique identifier to find existing plant
            botanical_name = row['Botanical Name']

            # Try to find an existing plant by botanical_name
            plant = Plant.query.filter_by(botanical_name=botanical_name).first()

            if plant:
                # Update the 'image_location' field
                plant.image_location = row['Image Location']
                updated_records += 1
            else:
                # Handle cases where the plant does not exist
                click.echo(f"Plant with botanical name '{botanical_name}' not found. Skipping.")
                skipped_records += 1
                continue

        db.session.commit()
        click.echo(f'Plant data has been updated successfully. {updated_records} records updated, {skipped_records} records skipped.')