import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# --- CONFIGURATION ---
app = Flask(__name__)

# Use SQLite for easy local testing
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db) # Migrations are now enabled

# --- MODELS (Database Tables) ---

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    
    # Relationship: One User has Many Posts
    posts = db.relationship('Post', backref='author', lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign Key: Links this post to a specific User
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def to_dict(self):
        """Converts database object to JSON"""
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M'),
            "author": self.author.username, # <--- The JOIN (Fetches User name)
            "user_id": self.user_id
        }

# --- AUTH ROUTES ---

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    # Validation
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({"error": "Username and password required"}), 400

    # Check duplicate user
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"error": "User already exists"}), 400

    # Hash Password
    hashed_pw = generate_password_hash(data['password'], method='pbkdf2:sha256')
    
    new_user = User(username=data['username'], password_hash=hashed_pw)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "User created successfully"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data.get('username')).first()

    # Check Password Hash
    if not user or not check_password_hash(user.password_hash, data.get('password')):
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({"message": f"Welcome {user.username}", "user_id": user.id}), 200

# --- POST ROUTES (CRUD) ---

# CREATE
@app.route('/posts', methods=['POST'])
def create_post():
    data = request.json
    user_id = data.get('user_id')
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    new_post = Post(title=data['title'], body=data['body'], author=user)
    db.session.add(new_post)
    db.session.commit()
    return jsonify(new_post.to_dict()), 201

# READ ALL
@app.route('/posts', methods=['GET'])
def get_posts():
    posts = Post.query.all()
    return jsonify([p.to_dict() for p in posts]), 200

# UPDATE (Protected)
@app.route('/posts/<int:id>', methods=['PUT'])
def update_post(id):
    post = Post.query.get_or_404(id)
    data = request.json
    
    # Authorization Check
    if int(data.get('user_id')) != post.user_id:
        return jsonify({"error": "Permission denied"}), 403

    post.title = data.get('title', post.title)
    post.body = data.get('body', post.body)
    db.session.commit()
    return jsonify({"message": "Updated", "post": post.to_dict()}), 200

# DELETE (Protected)
@app.route('/posts/<int:id>', methods=['DELETE'])
def delete_post(id):
    post = Post.query.get_or_404(id)
    data = request.json
    
    # Authorization Check
    if not data or int(data.get('user_id')) != post.user_id:
        return jsonify({"error": "Permission denied"}), 403

    try:
        db.session.delete(post)
        db.session.commit()
        return jsonify({"message": "Deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- FILTER ROUTE ---
@app.route('/users/<string:username>/posts', methods=['GET'])
def get_user_posts(username):
    user = User.query.filter_by(username=username).first_or_404()
    return jsonify([p.to_dict() for p in user.posts]), 200

if __name__ == '__main__':
    app.run(debug=True)