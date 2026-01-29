import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
from dotenv import load_dotenv

# Lesson: Load environment variables for security (.env)
load_dotenv()

app = Flask(__name__)

# --- CONFIGURATION ---
# Using getenv allows the app to work on your laptop and a real server
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --- DATABASE MODEL ---
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    priority = db.Column(db.String(20), default="Medium")
    is_done = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Helper to format database objects into JSON for the frontend"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "status": "Completed" if self.is_done else "Pending",
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M')
        }

# --- ROUTES (CRUD) ---

# 1. CREATE (POST)
@app.route('/tasks', methods=['POST'])
def create_task():
    data = request.json
    # Developer check: Validate input
    if not data or 'title' not in data:
        return jsonify({"error": "Title is required"}), 400
    
    new_task = Task(
        title=data['title'],
        description=data.get('description'),
        priority=data.get('priority', 'Medium')
    )
    db.session.add(new_task)
    db.session.commit()
    return jsonify(new_task.to_dict()), 201

# 2. READ ALL (GET)
@app.route('/tasks', methods=['GET'])
def get_tasks():
    tasks = Task.query.all()
    return jsonify([t.to_dict() for t in tasks]), 200

# 3. UPDATE (PUT)
@app.route('/tasks/<int:id>', methods=['PUT'])
def update_task(id):
    task = Task.query.get_or_404(id) # Returns 404 automatically if ID not found
    task.is_done = True
    db.session.commit()
    return jsonify({"message": "Task marked as complete", "task": task.to_dict()}), 200

# 4. DELETE (DELETE)
@app.route('/tasks/<int:id>', methods=['DELETE'])
def delete_task(id):
    task = Task.query.get_or_404(id)
    try:
        db.session.delete(task)
        db.session.commit()
        return jsonify({"message": "Task deleted successfully", "id": id}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Delete failed", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)