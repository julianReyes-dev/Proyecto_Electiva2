from flask import Flask, render_template, request, redirect, url_for, flash
from pymongo import MongoClient, monitoring
from pymongo.errors import ConnectionFailure
from bson import ObjectId
from dotenv import load_dotenv
import os
import datetime

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "secret-key-for-flash-messages")

# Database connection setup
uri = os.getenv("MONGO_URI")
db_name = os.getenv("DB_NAME", "test_database")
collection_name = os.getenv("COLLECTION_NAME", "personas")

# Command logger for database operations visualization
class CommandLogger(monitoring.CommandListener):
    def started(self, event):
        app.logger.info(f"Command {event.command_name} started on {event.connection_id}")

    def succeeded(self, event):
        app.logger.info(f"Command {event.command_name} succeeded in {event.duration_micros} μs")

    def failed(self, event):
        app.logger.info(f"Command {event.command_name} failed in {event.duration_micros} μs")

# Register the logger
monitoring.register(CommandLogger())

try:
    client = MongoClient(uri)
    db = client[db_name]
    collection = db[collection_name]
    # Test the connection
    client.admin.command('ping')
    db_status = {
        'connected': True,
        'last_check': datetime.datetime.now(),
        'server_info': client.server_info(),
        'stats': db.command('dbstats')
    }
    print("Successfully connected to MongoDB Atlas")
except ConnectionFailure as e:
    db_status = {
        'connected': False,
        'error': str(e),
        'last_check': datetime.datetime.now()
    }
    print("Error connecting to MongoDB Atlas")

@app.route('/')
def show_people():
    people = list(collection.find().limit(100))  # Limit to 100 records for demonstration
    
    # Get collection stats using db.command()
    try:
        stats = db.command('collstats', collection_name)
    except Exception as e:
        stats = {'error': str(e)}
    
    return render_template('index.html', 
                         people=people, 
                         db_status=db_status,
                         stats=stats)

@app.route('/add', methods=['GET', 'POST'])
def add_person():
    if request.method == 'POST':
        try:
            new_person = {
                'nombre': request.form['nombre'],
                'edad': int(request.form['edad']),
                'ciudad': request.form['ciudad'],
                'created_at': datetime.datetime.now()
            }
            result = collection.insert_one(new_person)
            flash(f"Person added successfully! ID: {result.inserted_id}", "success")
            return redirect(url_for('show_people'))
        except Exception as e:
            flash(f"Error adding person: {str(e)}", "danger")
    return render_template('add.html')

@app.route('/edit/<person_id>', methods=['GET', 'POST'])
def edit_person(person_id):
    person = collection.find_one({'_id': ObjectId(person_id)})
    if not person:
        flash("Person not found!", "danger")
        return redirect(url_for('show_people'))
    
    if request.method == 'POST':
        try:
            updated_person = {
                'nombre': request.form['nombre'],
                'edad': int(request.form['edad']),
                'ciudad': request.form['ciudad'],
                'updated_at': datetime.datetime.now()
            }
            result = collection.update_one(
                {'_id': ObjectId(person_id)},
                {'$set': updated_person}
            )
            flash(f"Person updated successfully! Modified count: {result.modified_count}", "success")
            return redirect(url_for('show_people'))
        except Exception as e:
            flash(f"Error updating person: {str(e)}", "danger")
    return render_template('edit.html', person=person)

@app.route('/delete/<person_id>')
def delete_person(person_id):
    try:
        result = collection.delete_one({'_id': ObjectId(person_id)})
        if result.deleted_count > 0:
            flash(f"Person deleted successfully! Deleted count: {result.deleted_count}", "success")
        else:
            flash("No person found with that ID!", "warning")
    except Exception as e:
        flash(f"Error deleting person: {str(e)}", "danger")
    return redirect(url_for('show_people'))

@app.route('/database-info')
def database_info():
    try:
        # Get active sessions
        sessions = list(client.admin.command('currentOp')['inprog'])
        # Get collection stats
        coll_stats = db.command('collstats', collection_name)
        # Get database stats
        db_stats = db.command('dbstats')
        return render_template('database_info.html',
                            sessions=sessions,
                            stats=coll_stats,
                            db_stats=db_stats,
                            db_status=db_status)
    except Exception as e:
        flash(f"Error getting database info: {str(e)}", "danger")
        return redirect(url_for('show_people'))

if __name__ == '__main__':
    app.run(debug=True)