"""
AssetVault - Enterprise IT Asset Management System
Consolidated Single-File Flask Application (app.py)
Includes Configuration, Database Layer, Auth & Helpers, Validators, and all Routes.
"""

import os
import sys
import re
from datetime import datetime, timedelta
from functools import wraps
from bson import ObjectId
from dotenv import load_dotenv
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify
)
from flask_cors import CORS
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure
from werkzeug.security import generate_password_hash, check_password_hash

# ==============================================================================
# 1. CONFIGURATION
# ==============================================================================

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'assetvault-default-key-replace-in-prod')
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
    DB_NAME = os.getenv('DB_NAME', 'asset_management')
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@assetvault.internal')
    APP_PORT = int(os.getenv('APP_PORT', 5000))
    DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 't')
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours

# ==============================================================================
# 2. DATABASE LAYER (MongoDB Connection & Schema Initialization)
# ==============================================================================

_client = None
_db = None

def get_db():
    """Connect to MongoDB and return the database instance."""
    global _client, _db
    if _db is None:
        try:
            _client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=5000)
            _client.admin.command('ping')
            _db = _client[Config.DB_NAME]
        except ConnectionFailure as e:
            print(f"Error: Could not connect to MongoDB at {Config.MONGO_URI}: {e}", file=sys.stderr)
            raise e
    return _db


def init_db():
    """Initialize collections, create indexes, and create default admin account if not present."""
    database = get_db()
    
    # 1. assets indexes
    database.assets.create_index([("asset_id", ASCENDING)], unique=True)
    database.assets.create_index([("serial_number", ASCENDING)], unique=True, sparse=True)
    database.assets.create_index([("status", ASCENDING)])
    database.assets.create_index([("category", ASCENDING)])
    database.assets.create_index([("department", ASCENDING)])
    database.assets.create_index([("location", ASCENDING)])
    database.assets.create_index([("asset_name", ASCENDING)])
    database.assets.create_index([("created_at", DESCENDING)])
    
    # 2. users indexes
    database.users.create_index([("user_id", ASCENDING)], unique=True)
    database.users.create_index([("email", ASCENDING)], unique=True, sparse=True)
    database.users.create_index([("department", ASCENDING)])
    
    # 3. departments indexes
    database.departments.create_index([("name", ASCENDING)], unique=True)
    database.departments.create_index([("geo_location", "2dsphere")], sparse=True)
    
    # 4. locations indexes
    database.locations.create_index([("name", ASCENDING)], unique=True)
    database.locations.create_index([("geo_location", "2dsphere")], sparse=True)
    
    # 5. categories indexes
    database.categories.create_index([("name", ASCENDING)], unique=True)
    
    # 6. assignments indexes
    database.assignments.create_index([("assignment_id", ASCENDING)], unique=True)
    database.assignments.create_index([("asset_id", ASCENDING)])
    database.assignments.create_index([("user_id", ASCENDING)])
    database.assignments.create_index([("status", ASCENDING)])
    
    # 7. maintenance indexes
    database.maintenance.create_index([("maintenance_id", ASCENDING)], unique=True)
    database.maintenance.create_index([("asset_id", ASCENDING)])
    database.maintenance.create_index([("status", ASCENDING)])
    
    # 8. asset_history indexes
    database.asset_history.create_index([("asset_id", ASCENDING)])
    database.asset_history.create_index([("timestamp", DESCENDING)])
    
    # 9. admin_users indexes
    database.admin_users.create_index([("username", ASCENDING)], unique=True)
    
    # Ensure default admin exists
    admin = database.admin_users.find_one({"username": Config.ADMIN_USERNAME})
    if not admin:
        database.admin_users.insert_one({
            "username": Config.ADMIN_USERNAME,
            "password_hash": generate_password_hash(Config.ADMIN_PASSWORD),
            "email": Config.ADMIN_EMAIL,
            "role": "Super Admin",
            "full_name": "System Administrator",
            "created_at": "2026-01-01T00:00:00Z"
        })
        print(f"Default admin '{Config.ADMIN_USERNAME}' created.")


def generate_next_id(collection_name, prefix, id_field, pad_length=4):
    """Generate incremental IDs like AST-0001, USR-001, ASN-0001, MNT-0001"""
    database = get_db()
    last_doc = database[collection_name].find_one(
        {id_field: {"$regex": f"^{prefix}-"}},
        projection={id_field: 1},
        sort=[(id_field, DESCENDING)]
    )
    
    if not last_doc or id_field not in last_doc:
        next_num = 1
    else:
        last_id = last_doc[id_field]
        try:
            num_part = int(last_id.split("-")[-1])
            next_num = num_part + 1
        except (ValueError, IndexError):
            next_num = database[collection_name].count_documents({}) + 1
            
    while True:
        candidate_id = f"{prefix}-{str(next_num).zfill(pad_length)}"
        if not database[collection_name].find_one({id_field: candidate_id}):
            return candidate_id
        next_num += 1

# ==============================================================================
# 3. CONSTANTS & VALIDATORS
# ==============================================================================

VALID_STATUSES = [
    "Available",
    "Assigned",
    "Under Maintenance",
    "Damaged",
    "Lost",
    "Retired",
    "Disposed"
]

VALID_CONDITIONS = [
    "Excellent",
    "Good",
    "Fair",
    "Poor",
    "Critical"
]

VALID_MAINTENANCE_STATUSES = [
    "Pending",
    "In Progress",
    "Completed",
    "Cancelled"
]

VALID_MAINTENANCE_TYPES = [
    "Preventive",
    "Corrective / Repair",
    "Software Update",
    "Hardware Upgrade",
    "Calibration",
    "Inspection / Audit"
]

def parse_coordinates(lat_val, lng_val):
    """Parse and validate latitude and longitude for MongoDB GeoJSON."""
    try:
        if lat_val and lng_val and str(lat_val).strip() and str(lng_val).strip():
            lat = float(str(lat_val).strip())
            lng = float(str(lng_val).strip())
            if -90 <= lat <= 90 and -180 <= lng <= 180:
                return lat, lng, {"type": "Point", "coordinates": [lng, lat]}
        return None, None, None
    except (ValueError, TypeError):
        return None, None, None

def validate_asset_data(data, is_update=False):
    errors = []
    
    asset_name = (data.get('asset_name') or '').strip()
    if not asset_name:
        errors.append("Asset Name is required.")
        
    category = (data.get('category') or '').strip()
    if not category:
        errors.append("Category is required.")
        
    brand = (data.get('brand') or '').strip()
    if not brand:
        errors.append("Brand is required.")
        
    serial_number = (data.get('serial_number') or '').strip()
    if not serial_number:
        errors.append("Serial Number is required.")
        
    department = (data.get('department') or '').strip()
    if not department:
        errors.append("Department is required.")
        
    location = (data.get('location') or '').strip()
    if not location:
        errors.append("Location is required.")
        
    status = (data.get('status') or 'Available').strip()
    if status not in VALID_STATUSES:
        errors.append(f"Invalid status '{status}'. Must be one of {', '.join(VALID_STATUSES)}.")
        
    condition = (data.get('condition') or 'Good').strip()
    if condition not in VALID_CONDITIONS:
        errors.append(f"Invalid condition '{condition}'. Must be one of {', '.join(VALID_CONDITIONS)}.")
        
    # Cost validation
    purchase_cost = data.get('purchase_cost')
    if purchase_cost is not None and purchase_cost != '':
        try:
            val = float(purchase_cost)
            if val < 0:
                errors.append("Purchase cost cannot be negative.")
        except ValueError:
            errors.append("Purchase cost must be a valid number.")
            
    # Date validations
    purchase_date = data.get('purchase_date')
    if purchase_date:
        try:
            datetime.strptime(str(purchase_date).strip()[:10], '%Y-%m-%d')
        except ValueError:
            errors.append("Purchase Date must be in YYYY-MM-DD format.")
            
    warranty_expiry = data.get('warranty_expiry')
    if warranty_expiry:
        try:
            datetime.strptime(str(warranty_expiry).strip()[:10], '%Y-%m-%d')
        except ValueError:
            errors.append("Warranty Expiry Date must be in YYYY-MM-DD format.")
            
    return errors

def validate_user_data(data):
    errors = []
    name = (data.get('name') or '').strip()
    if not name:
        errors.append("User Name is required.")
        
    email = (data.get('email') or '').strip()
    if not email:
        errors.append("Email is required.")
    elif not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
        errors.append("Invalid email format.")
        
    department = (data.get('department') or '').strip()
    if not department:
        errors.append("Department is required.")
        
    return errors

# ==============================================================================
# 4. AUTH & HELPER FUNCTIONS
# ==============================================================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or 'username' not in session:
            if request.path.startswith('/api/') or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"success": False, "message": "Authentication required"}), 401
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    if 'username' in session:
        return {
            "username": session.get('username'),
            "role": session.get('role', 'Admin'),
            "email": session.get('email', '')
        }
    return None

def get_current_timestamp():
    return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

def log_asset_history(asset_id, action, description, performed_by=None, metadata=None):
    """
    Records an entry in asset_history collection.
    Actions: Created, Updated, Assigned, Returned, Moved, Maintenance Started,
             Maintenance Completed, Maintenance Cancelled, Status Changed, Condition Changed, Deleted
    """
    db = get_db()
    if performed_by is None:
        performed_by = session.get('username', 'system')
        
    entry = {
        "asset_id": asset_id,
        "action": action,
        "description": description,
        "performed_by": performed_by,
        "timestamp": get_current_timestamp(),
        "metadata": metadata or {}
    }
    db.asset_history.insert_one(entry)
    return entry

def serialize_doc(doc):
    """Recursively converts MongoDB BSON objects (like ObjectId) into JSON-serializable types."""
    if doc is None:
        return None
    if isinstance(doc, list):
        return [serialize_doc(item) for item in doc]
    if isinstance(doc, dict):
        res = {}
        for k, v in doc.items():
            if isinstance(v, ObjectId):
                res[k] = str(v)
            elif isinstance(v, datetime):
                res[k] = v.isoformat()
            elif isinstance(v, (dict, list)):
                res[k] = serialize_doc(v)
            else:
                res[k] = v
        return res
    if isinstance(doc, ObjectId):
        return str(doc)
    if isinstance(doc, datetime):
        return doc.isoformat()
    return doc

def serialize_docs(docs):
    return [serialize_doc(d) for d in docs]

def format_currency(value):
    try:
        val = float(value)
        return f"₹{val:,.2f}"
    except (ValueError, TypeError):
        return "₹0.00"

def format_date(value):
    if not value:
        return "N/A"
    try:
        if isinstance(value, datetime):
            return value.strftime('%b %d, %Y')
        val_str = str(value).strip()[:10]
        dt = datetime.strptime(val_str, '%Y-%m-%d')
        return dt.strftime('%b %d, %Y')
    except Exception:
        return str(value)

def get_status_badge_class(status):
    mapping = {
        'Available': 'bg-success',
        'Assigned': 'bg-primary',
        'Under Maintenance': 'bg-warning text-dark',
        'Damaged': 'bg-danger',
        'Lost': 'bg-dark',
        'Retired': 'bg-secondary',
        'Disposed': 'bg-dark text-muted'
    }
    return mapping.get(status, 'bg-info')

def get_condition_badge_class(condition):
    mapping = {
        'Excellent': 'badge-subtle-success',
        'Good': 'badge-subtle-primary',
        'Fair': 'badge-subtle-warning',
        'Poor': 'badge-subtle-danger',
        'Critical': 'badge-subtle-critical'
    }
    return mapping.get(condition, 'badge-subtle-secondary')

# ==============================================================================
# 5. ALL APPLICATION ROUTES REGISTRATION
# ==============================================================================

def register_all_routes(app):
    """Register all authentication, dashboard, asset, user, department, location,
    assignment, maintenance, audit history, reports, and API routes on the Flask app."""

    # --------------------------------------------------------------------------
    # AUTHENTICATION ROUTES
    # --------------------------------------------------------------------------
    @app.route('/login', methods=['GET', 'POST'], endpoint='auth.login')
    def login():
        if 'user_id' in session and 'username' in session:
            return redirect(url_for('dashboard.index'))
            
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            
            if not username or not password:
                return render_template('login.html', username=username)
                
            db = get_db()
            admin = db.admin_users.find_one({"username": username})
            
            if admin and check_password_hash(admin.get('password_hash', ''), password):
                session.clear()
                session['user_id'] = str(admin.get('_id'))
                session['username'] = admin.get('username')
                session['role'] = admin.get('role', 'Super Admin')
                session['full_name'] = admin.get('full_name', 'Administrator')
                session['email'] = admin.get('email', '')
                session.permanent = True
                
                next_page = request.args.get('next')
                if next_page and next_page.startswith('/'):
                    return redirect(next_page)
                return redirect(url_for('dashboard.index'))
            else:
                return render_template('login.html', username=username)
                
        return render_template('login.html')

    @app.route('/logout', endpoint='auth.logout')
    def logout():
        session.clear()
        return redirect(url_for('auth.login'))

    # --------------------------------------------------------------------------
    # DASHBOARD ROUTES
    # --------------------------------------------------------------------------
    @app.route('/', endpoint='dashboard.home')
    def home():
        return redirect(url_for('dashboard.index'))

    @app.route('/dashboard', endpoint='dashboard.index')
    @login_required
    def dashboard_index():
        db = get_db()
        all_assets = list(db.assets.find({}))
        
        total_assets = len(all_assets)
        available_assets = sum(1 for a in all_assets if a.get('status') == 'Available')
        assigned_assets = sum(1 for a in all_assets if a.get('status') == 'Assigned')
        maintenance_assets = sum(1 for a in all_assets if a.get('status') == 'Under Maintenance')
        damaged_assets = sum(1 for a in all_assets if a.get('status') == 'Damaged')
        lost_assets = sum(1 for a in all_assets if a.get('status') == 'Lost')
        retired_assets = sum(1 for a in all_assets if a.get('status') == 'Retired')
        disposed_assets = sum(1 for a in all_assets if a.get('status') == 'Disposed')
        total_value = sum(float(a.get('purchase_cost') or 0) for a in all_assets)
        
        recent_activities = list(db.asset_history.find().sort("timestamp", -1).limit(10))
        active_maintenance = list(db.maintenance.find(
            {"status": {"$in": ["Pending", "In Progress"]}}
        ).sort("start_date", -1).limit(6))
        
        now = datetime.utcnow()
        today_str = now.strftime('%Y-%m-%d')
        in_60_days = (now + timedelta(days=60)).strftime('%Y-%m-%d')
        
        expiring_warranty_assets = list(db.assets.find({
            "warranty_expiry": {"$gte": today_str, "$lte": in_60_days}
        }).limit(5))
        
        overdue_assignments = list(db.assignments.find({
            "status": "Active",
            "expected_return_date": {"$lt": today_str, "$ne": None, "$ne": ""}
        }).limit(5))
        
        critical_condition_assets = list(db.assets.find({
            "condition": {"$in": ["Critical", "Poor"]}
        }).limit(5))
        
        stats = {
            "total_assets": total_assets,
            "available_assets": available_assets,
            "assigned_assets": assigned_assets,
            "maintenance_assets": maintenance_assets,
            "damaged_assets": damaged_assets,
            "lost_assets": lost_assets,
            "retired_assets": retired_assets,
            "disposed_assets": disposed_assets,
            "total_value": total_value,
            "total_value_formatted": format_currency(total_value),
            "total_users": db.users.count_documents({}),
            "total_departments": db.departments.count_documents({}),
            "total_locations": db.locations.count_documents({}),
        }
        
        alerts = {
            "expiring_warranty": expiring_warranty_assets,
            "overdue_assignments": overdue_assignments,
            "critical_condition": critical_condition_assets,
            "damaged_count": damaged_assets,
            "lost_count": lost_assets,
            "maintenance_count": maintenance_assets
        }
        
        return render_template(
            'dashboard.html',
            stats=stats,
            recent_activities=recent_activities,
            active_maintenance=active_maintenance,
            alerts=alerts
        )

    # --------------------------------------------------------------------------
    # ASSET MANAGEMENT ROUTES (CRUD + Assign, Return, Move)
    # --------------------------------------------------------------------------
    @app.route('/assets', endpoint='assets.index')
    @login_required
    def assets_index():
        db = get_db()
        
        search = request.args.get('search', '').strip()
        category = request.args.get('category', '').strip()
        status = request.args.get('status', '').strip()
        condition = request.args.get('condition', '').strip()
        department = request.args.get('department', '').strip()
        location = request.args.get('location', '').strip()
        alert = request.args.get('alert', '').strip()
        
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        if page < 1:
            page = 1
            
        query = {}
        if search:
            query["$or"] = [
                {"asset_id": {"$regex": search, "$options": "i"}},
                {"asset_name": {"$regex": search, "$options": "i"}},
                {"serial_number": {"$regex": search, "$options": "i"}},
                {"brand": {"$regex": search, "$options": "i"}},
                {"model": {"$regex": search, "$options": "i"}},
                {"assigned_to.name": {"$regex": search, "$options": "i"}}
            ]
            
        if category:
            query["category"] = category
        if status:
            query["status"] = status
        if condition:
            if ',' in condition:
                cond_list = [c.strip() for c in condition.split(',') if c.strip()]
                query["condition"] = {"$in": cond_list}
            elif condition in ["Critical/Poor", "critical_poor", "warning"]:
                query["condition"] = {"$in": ["Critical", "Poor"]}
            else:
                query["condition"] = condition
        if department:
            query["department"] = department
        if location:
            query["location"] = location

        now = datetime.utcnow()
        today_str = now.strftime('%Y-%m-%d')
        in_60_days = (now + timedelta(days=60)).strftime('%Y-%m-%d')

        if alert == 'warranty':
            query["warranty_expiry"] = {"$gte": today_str, "$lte": in_60_days}
        elif alert == 'condition' or alert == 'critical':
            query["condition"] = {"$in": ["Critical", "Poor"]}
        elif alert == 'damaged':
            query["status"] = "Damaged"
        elif alert == 'maintenance':
            query["status"] = "Under Maintenance"

        total_assets = db.assets.count_documents(query)
        total_pages = max(1, (total_assets + per_page - 1) // per_page)
        if page > total_pages:
            page = total_pages
            
        skip = (page - 1) * per_page
        assets_list = list(db.assets.find(query).sort("created_at", -1).skip(skip).limit(per_page))

        for a in assets_list:
            w_exp = a.get('warranty_expiry')
            a['is_warranty_expiring'] = bool(w_exp and today_str <= w_exp <= in_60_days)
            a['is_warranty_expired'] = bool(w_exp and w_exp < today_str)
            a['is_critical_condition'] = a.get('condition') in ['Critical', 'Poor']
        
        categories = list(db.categories.find().sort("name", 1))
        departments = list(db.departments.find().sort("name", 1))
        locations = list(db.locations.find().sort("name", 1))
        users = list(db.users.find({"status": "Active"}).sort("name", 1))
        
        return render_template(
            'assets/index.html',
            assets=assets_list,
            categories=categories,
            departments=departments,
            locations=locations,
            users=users,
            statuses=VALID_STATUSES,
            conditions=VALID_CONDITIONS,
            search=search,
            selected_category=category,
            selected_status=status,
            selected_condition=condition,
            selected_department=department,
            selected_location=location,
            selected_alert=alert,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            total_assets=total_assets
        )

    @app.route('/assets/add', methods=['GET', 'POST'], endpoint='assets.add')
    @login_required
    def assets_add():
        db = get_db()
        
        if request.method == 'POST':
            form_data = request.form.to_dict()
            errors = validate_asset_data(form_data)
            
            serial_number = form_data.get('serial_number', '').strip()
            if serial_number and db.assets.find_one({"serial_number": serial_number}):
                errors.append(f"An asset with serial number '{serial_number}' already exists.")
                
            if errors:
                categories = list(db.categories.find().sort("name", 1))
                departments = list(db.departments.find().sort("name", 1))
                locations = list(db.locations.find().sort("name", 1))
                return render_template('assets/add.html', asset=form_data, categories=categories, departments=departments, locations=locations, statuses=VALID_STATUSES, conditions=VALID_CONDITIONS)
                
            asset_id = generate_next_id('assets', 'AST', 'asset_id', 4)
            
            try:
                purchase_cost = float(form_data.get('purchase_cost', 0) or 0)
            except ValueError:
                purchase_cost = 0.0
                
            now_ts = get_current_timestamp()
            
            new_asset = {
                "asset_id": asset_id,
                "asset_name": form_data.get('asset_name', '').strip(),
                "category": form_data.get('category', '').strip(),
                "brand": form_data.get('brand', '').strip(),
                "model": form_data.get('model', '').strip(),
                "serial_number": serial_number,
                "purchase_date": form_data.get('purchase_date', ''),
                "purchase_cost": purchase_cost,
                "supplier": form_data.get('supplier', '').strip(),
                "department": form_data.get('department', '').strip(),
                "location": form_data.get('location', '').strip(),
                "status": form_data.get('status', 'Available'),
                "condition": form_data.get('condition', 'Good'),
                "assigned_to": None,
                "warranty_expiry": form_data.get('warranty_expiry', ''),
                "description": form_data.get('description', '').strip(),
                "created_at": now_ts,
                "updated_at": now_ts
            }
            
            db.assets.insert_one(new_asset)
            
            log_asset_history(
                asset_id=asset_id,
                action="Created",
                description=f"Asset '{new_asset['asset_name']}' created with ID {asset_id}."
            )
            
            return redirect(url_for('assets.view', asset_id=asset_id))
            
        categories = list(db.categories.find().sort("name", 1))
        departments = list(db.departments.find().sort("name", 1))
        locations = list(db.locations.find().sort("name", 1))
        
        return render_template(
            'assets/add.html',
            categories=categories,
            departments=departments,
            locations=locations,
            statuses=VALID_STATUSES,
            conditions=VALID_CONDITIONS,
            asset={}
        )

    @app.route('/assets/view/<asset_id>', endpoint='assets.view')
    @login_required
    def assets_view(asset_id):
        db = get_db()
        asset = db.assets.find_one({"asset_id": asset_id})
        if not asset:
            return redirect(url_for('assets.index'))
            
        history = list(db.asset_history.find({"asset_id": asset_id}).sort("timestamp", -1))
        active_assignment = db.assignments.find_one({"asset_id": asset_id, "status": "Active"})
        maintenance_records = list(db.maintenance.find({"asset_id": asset_id}).sort("start_date", -1))
        
        users = list(db.users.find({"status": "Active"}).sort("name", 1))
        locations = list(db.locations.find().sort("name", 1))
        departments = list(db.departments.find().sort("name", 1))
        
        return render_template(
            'assets/view.html',
            asset=asset,
            history=history,
            active_assignment=active_assignment,
            maintenance_records=maintenance_records,
            users=users,
            locations=locations,
            departments=departments,
            statuses=VALID_STATUSES,
            conditions=VALID_CONDITIONS,
            today=datetime.utcnow().strftime('%Y-%m-%d')
        )

    @app.route('/assets/edit/<asset_id>', methods=['GET', 'POST'], endpoint='assets.edit')
    @login_required
    def assets_edit(asset_id):
        db = get_db()
        asset = db.assets.find_one({"asset_id": asset_id})
        if not asset:
            return redirect(url_for('assets.index'))
            
        if request.method == 'POST':
            form_data = request.form.to_dict()
            errors = validate_asset_data(form_data, is_update=True)
            
            serial_number = form_data.get('serial_number', '').strip()
            existing_serial = db.assets.find_one({
                "serial_number": serial_number,
                "asset_id": {"$ne": asset_id}
            })
            if existing_serial:
                errors.append(f"Another asset already has serial number '{serial_number}'.")
                
            if errors:
                categories = list(db.categories.find().sort("name", 1))
                departments = list(db.departments.find().sort("name", 1))
                locations = list(db.locations.find().sort("name", 1))
                return render_template('assets/edit.html', asset=form_data, categories=categories, departments=departments, locations=locations, statuses=VALID_STATUSES, conditions=VALID_CONDITIONS)
                
            try:
                purchase_cost = float(form_data.get('purchase_cost', 0) or 0)
            except ValueError:
                purchase_cost = 0.0
                
            now_ts = get_current_timestamp()
            
            changes = []
            fields_to_check = ['asset_name', 'category', 'brand', 'model', 'department', 'location', 'status', 'condition', 'serial_number']
            for f in fields_to_check:
                old_val = asset.get(f)
                new_val = form_data.get(f)
                if str(old_val) != str(new_val):
                    changes.append(f"{f.replace('_', ' ').title()}: '{old_val}' → '{new_val}'")
                    
            update_doc = {
                "asset_name": form_data.get('asset_name', '').strip(),
                "category": form_data.get('category', '').strip(),
                "brand": form_data.get('brand', '').strip(),
                "model": form_data.get('model', '').strip(),
                "serial_number": serial_number,
                "purchase_date": form_data.get('purchase_date', ''),
                "purchase_cost": purchase_cost,
                "supplier": form_data.get('supplier', '').strip(),
                "department": form_data.get('department', '').strip(),
                "location": form_data.get('location', '').strip(),
                "status": form_data.get('status', asset.get('status', 'Available')),
                "condition": form_data.get('condition', asset.get('condition', 'Good')),
                "warranty_expiry": form_data.get('warranty_expiry', ''),
                "description": form_data.get('description', '').strip(),
                "updated_at": now_ts
            }
            
            db.assets.update_one({"asset_id": asset_id}, {"$set": update_doc})
            
            change_desc = "; ".join(changes) if changes else "Asset details updated."
            log_asset_history(
                asset_id=asset_id,
                action="Updated",
                description=f"Asset updated. {change_desc}"
            )
            
            return redirect(url_for('assets.view', asset_id=asset_id))
            
        categories = list(db.categories.find().sort("name", 1))
        departments = list(db.departments.find().sort("name", 1))
        locations = list(db.locations.find().sort("name", 1))
        
        return render_template(
            'assets/edit.html',
            asset=asset,
            categories=categories,
            departments=departments,
            locations=locations,
            statuses=VALID_STATUSES,
            conditions=VALID_CONDITIONS
        )

    @app.route('/assets/delete/<asset_id>', methods=['POST'], endpoint='assets.delete')
    @login_required
    def assets_delete(asset_id):
        db = get_db()
        asset = db.assets.find_one({"asset_id": asset_id})
        if not asset:
            return redirect(url_for('assets.index'))
            
        asset_name = asset.get('asset_name', asset_id)
        
        log_asset_history(
            asset_id=asset_id,
            action="Deleted",
            description=f"Asset '{asset_name}' ({asset_id}) was deleted from the system."
        )
        
        db.assignments.update_many(
            {"asset_id": asset_id, "status": "Active"},
            {"$set": {"status": "Closed", "return_date": datetime.utcnow().strftime('%Y-%m-%d'), "notes": "Asset deleted from inventory"}}
        )
        
        db.assets.delete_one({"asset_id": asset_id})
        return redirect(url_for('assets.index'))

    @app.route('/assets/<asset_id>/move', methods=['POST'], endpoint='assets.move')
    @login_required
    def assets_move(asset_id):
        db = get_db()
        asset = db.assets.find_one({"asset_id": asset_id})
        if not asset:
            return redirect(url_for('assets.index'))
            
        from_location = asset.get('location', 'Unknown')
        to_location = request.form.get('to_location', '').strip()
        reason = request.form.get('reason', '').strip() or 'Location transfer'
        
        if not to_location:
            return redirect(url_for('assets.view', asset_id=asset_id))
            
        db.assets.update_one(
            {"asset_id": asset_id},
            {"$set": {"location": to_location, "updated_at": get_current_timestamp()}}
        )
        
        log_asset_history(
            asset_id=asset_id,
            action="Moved",
            description=f"Moved from '{from_location}' to '{to_location}'. Reason: {reason}",
            metadata={"from_location": from_location, "to_location": to_location, "reason": reason}
        )
        
        return redirect(url_for('assets.view', asset_id=asset_id))

    @app.route('/assets/<asset_id>/assign', methods=['POST'], endpoint='assets.assign')
    @login_required
    def assets_assign(asset_id):
        db = get_db()
        asset = db.assets.find_one({"asset_id": asset_id})
        if not asset:
            return redirect(url_for('assets.index'))
            
        user_id = request.form.get('user_id', '').strip()
        assignment_date = request.form.get('assignment_date', datetime.utcnow().strftime('%Y-%m-%d')).strip()
        expected_return_date = request.form.get('expected_return_date', '').strip()
        notes = request.form.get('notes', '').strip()
        department = request.form.get('department', '').strip()
        
        user = db.users.find_one({"user_id": user_id})
        if not user:
            return redirect(url_for('assets.view', asset_id=asset_id))
            
        assigned_dept = department or user.get('department', asset.get('department', 'General'))
        assignment_id = generate_next_id('assignments', 'ASN', 'assignment_id', 4)
        
        assignment_doc = {
            "assignment_id": assignment_id,
            "asset_id": asset_id,
            "asset_name": asset.get('asset_name'),
            "user_id": user_id,
            "user_name": user.get('name'),
            "user_email": user.get('email'),
            "department": assigned_dept,
            "assigned_date": assignment_date,
            "expected_return_date": expected_return_date,
            "return_date": None,
            "status": "Active",
            "notes": notes,
            "created_at": get_current_timestamp()
        }
        db.assignments.insert_one(assignment_doc)
        
        assigned_obj = {
            "user_id": user_id,
            "name": user.get('name'),
            "email": user.get('email'),
            "assignment_date": assignment_date,
            "assignment_id": assignment_id
        }
        db.assets.update_one(
            {"asset_id": asset_id},
            {"$set": {
                "status": "Assigned",
                "assigned_to": assigned_obj,
                "department": assigned_dept,
                "updated_at": get_current_timestamp()
            }}
        )
        
        log_asset_history(
            asset_id=asset_id,
            action="Assigned",
            description=f"Assigned to {user.get('name')} ({user_id}) in department '{assigned_dept}'. Notes: {notes or 'None'}",
            metadata={"assignment_id": assignment_id, "user_id": user_id, "user_name": user.get('name')}
        )
        
        return redirect(url_for('assets.view', asset_id=asset_id))

    @app.route('/assets/<asset_id>/return', methods=['POST'], endpoint='assets.return_asset')
    @login_required
    def assets_return_asset(asset_id):
        db = get_db()
        asset = db.assets.find_one({"asset_id": asset_id})
        if not asset:
            return redirect(url_for('assets.index'))
            
        return_date = request.form.get('return_date', datetime.utcnow().strftime('%Y-%m-%d')).strip()
        return_condition = request.form.get('condition', asset.get('condition', 'Good')).strip()
        remarks = request.form.get('remarks', '').strip()
        
        active_asn = db.assignments.find_one({"asset_id": asset_id, "status": "Active"})
        user_name = active_asn.get('user_name', 'user') if active_asn else 'user'
        
        if active_asn:
            db.assignments.update_one(
                {"_id": active_asn['_id']},
                {"$set": {
                    "status": "Returned",
                    "return_date": return_date,
                    "return_condition": return_condition,
                    "return_remarks": remarks
                }}
            )
            
        db.assets.update_one(
            {"asset_id": asset_id},
            {"$set": {
                "status": "Available",
                "condition": return_condition,
                "assigned_to": None,
                "updated_at": get_current_timestamp()
            }}
        )
        
        log_asset_history(
            asset_id=asset_id,
            action="Returned",
            description=f"Asset returned from {user_name}. Condition: {return_condition}. Remarks: {remarks or 'None'}"
        )
        
        return redirect(url_for('assets.view', asset_id=asset_id))

    # --------------------------------------------------------------------------
    # USER MANAGEMENT ROUTES
    # --------------------------------------------------------------------------
    @app.route('/users', endpoint='users.index')
    @login_required
    def users_index():
        db = get_db()
        search = request.args.get('search', '').strip()
        department = request.args.get('department', '').strip()
        designation = request.args.get('designation', '').strip()
        
        query = {}
        if search:
            query["$or"] = [
                {"user_id": {"$regex": search, "$options": "i"}},
                {"name": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}},
                {"phone": {"$regex": search, "$options": "i"}}
            ]
        if department:
            query["department"] = department
        if designation:
            query["designation"] = designation
            
        users_list = list(db.users.find(query).sort("created_at", -1))
        
        for user in users_list:
            user_id = user.get('user_id')
            user['assigned_assets_count'] = db.assets.count_documents({
                "assigned_to.user_id": user_id,
                "status": "Assigned"
            })
            
        departments = list(db.departments.find().sort("name", 1))
        
        return render_template(
            'users/index.html',
            users=users_list,
            departments=departments,
            search=search,
            selected_department=department,
            selected_designation=designation
        )

    @app.route('/users/add', methods=['GET', 'POST'], endpoint='users.add')
    @login_required
    def users_add():
        db = get_db()
        
        if request.method == 'POST':
            form_data = request.form.to_dict()
            errors = validate_user_data(form_data)
            
            email = form_data.get('email', '').strip()
            if email and db.users.find_one({"email": email}):
                errors.append(f"A user with email '{email}' already exists.")
                
            if errors:
                departments = list(db.departments.find().sort("name", 1))
                return render_template('users/add.html', user=form_data, departments=departments)
                
            user_id = generate_next_id('users', 'USR', 'user_id', 3)
            now_ts = get_current_timestamp()
            
            new_user = {
                "user_id": user_id,
                "name": form_data.get('name', '').strip(),
                "email": email,
                "phone": form_data.get('phone', '').strip(),
                "department": form_data.get('department', '').strip(),
                "designation": form_data.get('designation', 'Staff').strip(),
                "status": form_data.get('status', 'Active'),
                "created_at": now_ts,
                "updated_at": now_ts
            }
            
            db.users.insert_one(new_user)
            return redirect(url_for('users.index'))
            
        departments = list(db.departments.find().sort("name", 1))
        return render_template('users/add.html', departments=departments, user={})

    @app.route('/users/view/<user_id>', endpoint='users.view')
    @login_required
    def users_view(user_id):
        db = get_db()
        user = db.users.find_one({"user_id": user_id})
        if not user:
            return redirect(url_for('users.index'))
            
        active_assets = list(db.assets.find({
            "assigned_to.user_id": user_id,
            "status": "Assigned"
        }))
        
        assignment_history = list(db.assignments.find({"user_id": user_id}).sort("assigned_date", -1))
        
        return render_template(
            'users/view.html',
            user=user,
            active_assets=active_assets,
            assignment_history=assignment_history
        )

    @app.route('/users/edit/<user_id>', methods=['GET', 'POST'], endpoint='users.edit')
    @login_required
    def users_edit(user_id):
        db = get_db()
        user = db.users.find_one({"user_id": user_id})
        if not user:
            return redirect(url_for('users.index'))
            
        if request.method == 'POST':
            form_data = request.form.to_dict()
            errors = validate_user_data(form_data)
            
            email = form_data.get('email', '').strip()
            existing_email = db.users.find_one({"email": email, "user_id": {"$ne": user_id}})
            if existing_email:
                errors.append(f"Another user already has the email '{email}'.")
                
            if errors:
                departments = list(db.departments.find().sort("name", 1))
                return render_template('users/edit.html', user=form_data, departments=departments)
                
            now_ts = get_current_timestamp()
            
            update_doc = {
                "name": form_data.get('name', '').strip(),
                "email": email,
                "phone": form_data.get('phone', '').strip(),
                "department": form_data.get('department', '').strip(),
                "designation": form_data.get('designation', '').strip(),
                "status": form_data.get('status', 'Active'),
                "updated_at": now_ts
            }
            
            db.users.update_one({"user_id": user_id}, {"$set": update_doc})
            
            db.assets.update_many(
                {"assigned_to.user_id": user_id},
                {"$set": {"assigned_to.name": update_doc['name'], "assigned_to.email": email}}
            )
            
            return redirect(url_for('users.index'))
            
        departments = list(db.departments.find().sort("name", 1))
        return render_template('users/edit.html', user=user, departments=departments)

    @app.route('/users/delete/<user_id>', methods=['POST'], endpoint='users.delete')
    @login_required
    def users_delete(user_id):
        db = get_db()
        user = db.users.find_one({"user_id": user_id})
        if not user:
            return redirect(url_for('users.index'))
            
        assigned_count = db.assets.count_documents({"assigned_to.user_id": user_id, "status": "Assigned"})
        if assigned_count > 0:
            return redirect(url_for('users.index'))
            
        db.users.delete_one({"user_id": user_id})
        return redirect(url_for('users.index'))

    # --------------------------------------------------------------------------
    # DEPARTMENT MANAGEMENT ROUTES
    # --------------------------------------------------------------------------
    @app.route('/departments', endpoint='departments.index')
    @login_required
    def departments_index():
        db = get_db()
        departments_list = list(db.departments.find().sort("name", 1))
        
        for dept in departments_list:
            dept_name = dept.get('name')
            dept['asset_count'] = db.assets.count_documents({"department": dept_name})
            
            pipeline = [
                {"$match": {"department": dept_name}},
                {"$group": {"_id": None, "total_value": {"$sum": "$purchase_cost"}}}
            ]
            res = list(db.assets.aggregate(pipeline))
            dept_val = res[0]['total_value'] if res else 0
            dept['total_value'] = dept_val
            dept['total_value_formatted'] = format_currency(dept_val)
            
        return render_template('departments/index.html', departments=departments_list)

    @app.route('/departments/add', methods=['POST'], endpoint='departments.add')
    @login_required
    def departments_add():
        db = get_db()
        name = request.form.get('name', '').strip()
        head = request.form.get('head', '').strip()
        email = request.form.get('email', '').strip()
        location = request.form.get('location', '').strip()
        description = request.form.get('description', '').strip()
        lat_val = request.form.get('latitude', '').strip()
        lng_val = request.form.get('longitude', '').strip()
        
        if not name or db.departments.find_one({"name": name}):
            return redirect(url_for('departments.index'))
            
        lat, lng, geo_loc = parse_coordinates(lat_val, lng_val)
        
        new_dept = {
            "name": name,
            "head": head,
            "email": email,
            "location": location,
            "description": description,
            "latitude": lat,
            "longitude": lng,
            "geo_location": geo_loc,
            "created_at": get_current_timestamp()
        }
        db.departments.insert_one(new_dept)
        return redirect(url_for('departments.index'))

    @app.route('/departments/edit/<dept_id>', methods=['POST'], endpoint='departments.edit')
    @login_required
    def departments_edit(dept_id):
        db = get_db()
        name = request.form.get('name', '').strip()
        head = request.form.get('head', '').strip()
        email = request.form.get('email', '').strip()
        location = request.form.get('location', '').strip()
        description = request.form.get('description', '').strip()
        lat_val = request.form.get('latitude', '').strip()
        lng_val = request.form.get('longitude', '').strip()
        
        if not name:
            return redirect(url_for('departments.index'))
            
        try:
            query = {"_id": ObjectId(dept_id)}
        except Exception:
            query = {"name": dept_id}
            
        dept = db.departments.find_one(query)
        if not dept:
            return redirect(url_for('departments.index'))
            
        old_name = dept.get('name')
        
        if name != old_name and db.departments.find_one({"name": name}):
            return redirect(url_for('departments.index'))
            
        lat, lng, geo_loc = parse_coordinates(lat_val, lng_val)
        
        update_data = {
            "name": name,
            "head": head,
            "email": email,
            "location": location,
            "description": description,
            "latitude": lat,
            "longitude": lng,
            "geo_location": geo_loc,
            "updated_at": get_current_timestamp()
        }
        
        db.departments.update_one(query, {"$set": update_data})
        
        if name != old_name:
            db.assets.update_many({"department": old_name}, {"$set": {"department": name}})
            db.users.update_many({"department": old_name}, {"$set": {"department": name}})
            
        return redirect(url_for('departments.index'))

    @app.route('/departments/delete/<dept_id>', methods=['POST'], endpoint='departments.delete')
    @login_required
    def departments_delete(dept_id):
        db = get_db()
        try:
            query = {"_id": ObjectId(dept_id)}
        except Exception:
            query = {"name": dept_id}
            
        dept = db.departments.find_one(query)
        if not dept:
            return redirect(url_for('departments.index'))
            
        dept_name = dept.get('name')
        asset_count = db.assets.count_documents({"department": dept_name})
        if asset_count > 0:
            return redirect(url_for('departments.index'))
            
        db.departments.delete_one(query)
        return redirect(url_for('departments.index'))

    # --------------------------------------------------------------------------
    # LOCATION MANAGEMENT ROUTES
    # --------------------------------------------------------------------------
    @app.route('/locations', endpoint='locations.index')
    @login_required
    def locations_index():
        db = get_db()
        locations_list = list(db.locations.find().sort("name", 1))
        
        for loc in locations_list:
            loc_name = loc.get('name')
            loc['asset_count'] = db.assets.count_documents({"location": loc_name})
            
        return render_template('locations/index.html', locations=locations_list)

    @app.route('/locations/add', methods=['POST'], endpoint='locations.add')
    @login_required
    def locations_add():
        db = get_db()
        name = request.form.get('name', '').strip()
        building = request.form.get('building', '').strip()
        floor = request.form.get('floor', '').strip()
        room = request.form.get('room', '').strip()
        description = request.form.get('description', '').strip()
        lat_val = request.form.get('latitude', '').strip()
        lng_val = request.form.get('longitude', '').strip()
        
        if not name or db.locations.find_one({"name": name}):
            return redirect(url_for('locations.index'))
            
        lat, lng, geo_loc = parse_coordinates(lat_val, lng_val)
        
        new_loc = {
            "name": name,
            "building": building,
            "floor": floor,
            "room": room,
            "description": description,
            "latitude": lat,
            "longitude": lng,
            "geo_location": geo_loc,
            "created_at": get_current_timestamp()
        }
        db.locations.insert_one(new_loc)
        return redirect(url_for('locations.index'))

    @app.route('/locations/edit/<loc_id>', methods=['POST'], endpoint='locations.edit')
    @login_required
    def locations_edit(loc_id):
        db = get_db()
        name = request.form.get('name', '').strip()
        building = request.form.get('building', '').strip()
        floor = request.form.get('floor', '').strip()
        room = request.form.get('room', '').strip()
        description = request.form.get('description', '').strip()
        lat_val = request.form.get('latitude', '').strip()
        lng_val = request.form.get('longitude', '').strip()
        
        if not name:
            return redirect(url_for('locations.index'))
            
        try:
            query = {"_id": ObjectId(loc_id)}
        except Exception:
            query = {"name": loc_id}
            
        loc = db.locations.find_one(query)
        if not loc:
            return redirect(url_for('locations.index'))
            
        old_name = loc.get('name')
        if name != old_name and db.locations.find_one({"name": name}):
            return redirect(url_for('locations.index'))
            
        lat, lng, geo_loc = parse_coordinates(lat_val, lng_val)
        
        update_data = {
            "name": name,
            "building": building,
            "floor": floor,
            "room": room,
            "description": description,
            "latitude": lat,
            "longitude": lng,
            "geo_location": geo_loc,
            "updated_at": get_current_timestamp()
        }
        
        db.locations.update_one(query, {"$set": update_data})
        
        if name != old_name:
            db.assets.update_many({"location": old_name}, {"$set": {"location": name}})
            
        return redirect(url_for('locations.index'))

    @app.route('/locations/delete/<loc_id>', methods=['POST'], endpoint='locations.delete')
    @login_required
    def locations_delete(loc_id):
        db = get_db()
        try:
            query = {"_id": ObjectId(loc_id)}
        except Exception:
            query = {"name": loc_id}
            
        loc = db.locations.find_one(query)
        if not loc:
            return redirect(url_for('locations.index'))
            
        loc_name = loc.get('name')
        asset_count = db.assets.count_documents({"location": loc_name})
        if asset_count > 0:
            return redirect(url_for('locations.index'))
            
        db.locations.delete_one(query)
        return redirect(url_for('locations.index'))

    # --------------------------------------------------------------------------
    # ASSIGNMENT MANAGEMENT ROUTES
    # --------------------------------------------------------------------------
    @app.route('/assignments', endpoint='assignments.index')
    @login_required
    def assignments_index():
        db = get_db()
        status_filter = request.args.get('status', '').strip()
        search = request.args.get('search', '').strip()
        
        today_str = datetime.utcnow().strftime('%Y-%m-%d')
        query = {}
        if status_filter == 'Overdue':
            query["status"] = "Active"
            query["expected_return_date"] = {"$lt": today_str, "$ne": None, "$ne": ""}
        elif status_filter:
            query["status"] = status_filter

        if search:
            query["$or"] = [
                {"assignment_id": {"$regex": search, "$options": "i"}},
                {"asset_id": {"$regex": search, "$options": "i"}},
                {"asset_name": {"$regex": search, "$options": "i"}},
                {"user_name": {"$regex": search, "$options": "i"}},
                {"user_id": {"$regex": search, "$options": "i"}},
                {"department": {"$regex": search, "$options": "i"}}
            ]
            
        assignments_list = list(db.assignments.find(query).sort("created_at", -1))
        
        for a in assignments_list:
            exp = a.get('expected_return_date')
            a['is_overdue'] = bool(a.get('status') == 'Active' and exp and exp < today_str)

        return render_template(
            'assignments/index.html',
            assignments=assignments_list,
            selected_status=status_filter,
            search=search,
            conditions=VALID_CONDITIONS
        )

    @app.route('/assignments/new', methods=['GET', 'POST'], endpoint='assignments.new')
    @login_required
    def assignments_new():
        db = get_db()
        
        if request.method == 'POST':
            asset_id = request.form.get('asset_id', '').strip()
            user_id = request.form.get('user_id', '').strip()
            department = request.form.get('department', '').strip()
            assigned_date = request.form.get('assigned_date', datetime.utcnow().strftime('%Y-%m-%d')).strip()
            expected_return_date = request.form.get('expected_return_date', '').strip()
            notes = request.form.get('notes', '').strip()
            
            asset = db.assets.find_one({"asset_id": asset_id})
            user = db.users.find_one({"user_id": user_id})
            
            if not asset or not user or asset.get('status') == 'Under Maintenance':
                return redirect(url_for('assignments.new'))
                
            assignment_id = generate_next_id('assignments', 'ASN', 'assignment_id', 4)
            assigned_dept = department or user.get('department') or asset.get('department', 'General')
            
            assignment_doc = {
                "assignment_id": assignment_id,
                "asset_id": asset_id,
                "asset_name": asset.get('asset_name'),
                "user_id": user_id,
                "user_name": user.get('name'),
                "user_email": user.get('email'),
                "department": assigned_dept,
                "assigned_date": assigned_date,
                "expected_return_date": expected_return_date,
                "return_date": None,
                "status": "Active",
                "notes": notes,
                "created_at": get_current_timestamp()
            }
            db.assignments.insert_one(assignment_doc)
            
            db.assets.update_one(
                {"asset_id": asset_id},
                {"$set": {
                    "status": "Assigned",
                    "assigned_to": {
                        "user_id": user_id,
                        "name": user.get('name'),
                        "email": user.get('email'),
                        "assignment_date": assigned_date,
                        "assignment_id": assignment_id
                    },
                    "department": assigned_dept,
                    "updated_at": get_current_timestamp()
                }}
            )
            
            log_asset_history(
                asset_id=asset_id,
                action="Assigned",
                description=f"Assigned to {user.get('name')} ({user_id}) in {assigned_dept}."
            )
            
            return redirect(url_for('assignments.index'))
            
        preselect_asset = request.args.get('asset_id', '')
        available_assets = list(db.assets.find({"status": {"$in": ["Available", "Assigned"]}}).sort("asset_name", 1))
        users = list(db.users.find({"status": "Active"}).sort("name", 1))
        departments = list(db.departments.find().sort("name", 1))
        
        return render_template(
            'assignments/new.html',
            available_assets=available_assets,
            users=users,
            departments=departments,
            preselect_asset=preselect_asset,
            today=datetime.utcnow().strftime('%Y-%m-%d')
        )

    @app.route('/assignments/return/<assignment_id>', methods=['POST'], endpoint='assignments.return_assignment')
    @login_required
    def assignments_return_assignment(assignment_id):
        db = get_db()
        asn = db.assignments.find_one({"assignment_id": assignment_id})
        if not asn:
            return redirect(url_for('assignments.index'))
            
        return_date = request.form.get('return_date', datetime.utcnow().strftime('%Y-%m-%d')).strip()
        return_condition = request.form.get('condition', 'Good').strip()
        remarks = request.form.get('remarks', '').strip()
        
        db.assignments.update_one(
            {"assignment_id": assignment_id},
            {"$set": {
                "status": "Returned",
                "return_date": return_date,
                "return_condition": return_condition,
                "return_remarks": remarks
            }}
        )
        
        asset_id = asn.get('asset_id')
        db.assets.update_one(
            {"asset_id": asset_id},
            {"$set": {
                "status": "Available",
                "condition": return_condition,
                "assigned_to": None,
                "updated_at": get_current_timestamp()
            }}
        )
        
        log_asset_history(
            asset_id=asset_id,
            action="Returned",
            description=f"Returned from assignment {assignment_id} by {asn.get('user_name')}. Condition: {return_condition}. Remarks: {remarks or 'None'}"
        )
        
        return redirect(url_for('assignments.index'))

    # --------------------------------------------------------------------------
    # MAINTENANCE TICKETS & TRACKING ROUTES
    # --------------------------------------------------------------------------
    @app.route('/maintenance', endpoint='maintenance.index')
    @login_required
    def maintenance_index():
        db = get_db()
        status_filter = request.args.get('status', '').strip()
        search = request.args.get('search', '').strip()
        
        query = {}
        if status_filter:
            query["status"] = status_filter
        if search:
            query["$or"] = [
                {"maintenance_id": {"$regex": search, "$options": "i"}},
                {"asset_id": {"$regex": search, "$options": "i"}},
                {"asset_name": {"$regex": search, "$options": "i"}},
                {"service_provider": {"$regex": search, "$options": "i"}},
                {"issue": {"$regex": search, "$options": "i"}}
            ]
            
        records = list(db.maintenance.find(query).sort("start_date", -1))
        
        for r in records:
            cost = r.get('cost', 0)
            r['cost_formatted'] = format_currency(cost)
            
        return render_template(
            'maintenance/index.html',
            records=records,
            selected_status=status_filter,
            search=search,
            statuses=VALID_MAINTENANCE_STATUSES,
            types=VALID_MAINTENANCE_TYPES,
            conditions=VALID_CONDITIONS
        )

    @app.route('/maintenance/new', methods=['GET', 'POST'], endpoint='maintenance.new')
    @login_required
    def maintenance_new():
        db = get_db()
        
        if request.method == 'POST':
            asset_id = request.form.get('asset_id', '').strip()
            maintenance_type = request.form.get('maintenance_type', 'Preventive').strip()
            issue = request.form.get('issue', '').strip()
            description = request.form.get('description', '').strip()
            service_provider = request.form.get('service_provider', '').strip()
            start_date = request.form.get('start_date', datetime.utcnow().strftime('%Y-%m-%d')).strip()
            expected_completion = request.form.get('expected_completion', '').strip()
            status = request.form.get('status', 'In Progress').strip()
            remarks = request.form.get('remarks', '').strip()
            
            try:
                cost = float(request.form.get('cost', 0) or 0)
            except ValueError:
                cost = 0.0
                
            asset = db.assets.find_one({"asset_id": asset_id})
            if not asset:
                return redirect(url_for('maintenance.new'))
                
            maintenance_id = generate_next_id('maintenance', 'MNT', 'maintenance_id', 4)
            
            doc = {
                "maintenance_id": maintenance_id,
                "asset_id": asset_id,
                "asset_name": asset.get('asset_name'),
                "maintenance_type": maintenance_type,
                "issue": issue,
                "description": description,
                "service_provider": service_provider,
                "start_date": start_date,
                "expected_completion": expected_completion,
                "actual_completion": None,
                "cost": cost,
                "status": status,
                "remarks": remarks,
                "created_at": get_current_timestamp()
            }
            db.maintenance.insert_one(doc)
            
            if status in ['Pending', 'In Progress']:
                db.assets.update_one(
                    {"asset_id": asset_id},
                    {"$set": {"status": "Under Maintenance", "updated_at": get_current_timestamp()}}
                )
                
            log_asset_history(
                asset_id=asset_id,
                action="Maintenance Started",
                description=f"Maintenance {maintenance_id} started ({maintenance_type}): {issue}. Provider: {service_provider or 'Internal'}"
            )
            
            return redirect(url_for('maintenance.index'))
            
        preselect_asset = request.args.get('asset_id', '')
        assets_list = list(db.assets.find().sort("asset_name", 1))
        
        return render_template(
            'maintenance/new.html',
            assets=assets_list,
            preselect_asset=preselect_asset,
            types=VALID_MAINTENANCE_TYPES,
            statuses=VALID_MAINTENANCE_STATUSES,
            today=datetime.utcnow().strftime('%Y-%m-%d')
        )

    @app.route('/maintenance/edit/<maintenance_id>', methods=['GET', 'POST'], endpoint='maintenance.edit')
    @login_required
    def maintenance_edit(maintenance_id):
        db = get_db()
        record = db.maintenance.find_one({"maintenance_id": maintenance_id})
        if not record:
            return redirect(url_for('maintenance.index'))
            
        if request.method == 'POST':
            maintenance_type = request.form.get('maintenance_type', 'Preventive').strip()
            issue = request.form.get('issue', '').strip()
            description = request.form.get('description', '').strip()
            service_provider = request.form.get('service_provider', '').strip()
            start_date = request.form.get('start_date', '').strip()
            expected_completion = request.form.get('expected_completion', '').strip()
            actual_completion = request.form.get('actual_completion', '').strip()
            status = request.form.get('status', 'In Progress').strip()
            remarks = request.form.get('remarks', '').strip()
            condition_after = request.form.get('condition_after', 'Good').strip()
            
            try:
                cost = float(request.form.get('cost', 0) or 0)
            except ValueError:
                cost = 0.0
                
            old_status = record.get('status')
            asset_id = record.get('asset_id')
            
            update_doc = {
                "maintenance_type": maintenance_type,
                "issue": issue,
                "description": description,
                "service_provider": service_provider,
                "start_date": start_date,
                "expected_completion": expected_completion,
                "actual_completion": actual_completion if status == 'Completed' else None,
                "cost": cost,
                "status": status,
                "remarks": remarks,
                "updated_at": get_current_timestamp()
            }
            
            db.maintenance.update_one({"maintenance_id": maintenance_id}, {"$set": update_doc})
            
            if status == 'Completed' and old_status != 'Completed':
                db.assets.update_one(
                    {"asset_id": asset_id},
                    {"$set": {
                        "status": "Available",
                        "condition": condition_after,
                        "updated_at": get_current_timestamp()
                    }}
                )
                log_asset_history(
                    asset_id=asset_id,
                    action="Maintenance Completed",
                    description=f"Maintenance {maintenance_id} marked as Completed. Condition set to {condition_after}. Total Cost: {format_currency(cost)}"
                )
            elif status == 'Cancelled' and old_status != 'Cancelled':
                other_m = db.maintenance.find_one({"asset_id": asset_id, "status": "In Progress", "maintenance_id": {"$ne": maintenance_id}})
                if not other_m:
                    db.assets.update_one(
                        {"asset_id": asset_id},
                        {"$set": {"status": "Available", "updated_at": get_current_timestamp()}}
                    )
                log_asset_history(
                    asset_id=asset_id,
                    action="Maintenance Cancelled",
                    description=f"Maintenance ticket {maintenance_id} was cancelled."
                )
            elif status in ['Pending', 'In Progress'] and old_status not in ['Pending', 'In Progress']:
                db.assets.update_one(
                    {"asset_id": asset_id},
                    {"$set": {"status": "Under Maintenance", "updated_at": get_current_timestamp()}}
                )
                
            return redirect(url_for('maintenance.index'))
            
        return render_template(
            'maintenance/edit.html',
            record=record,
            types=VALID_MAINTENANCE_TYPES,
            statuses=VALID_MAINTENANCE_STATUSES,
            conditions=VALID_CONDITIONS
        )

    @app.route('/maintenance/update-status/<maintenance_id>', methods=['POST'], endpoint='maintenance.update_status')
    @login_required
    def maintenance_update_status(maintenance_id):
        db = get_db()
        record = db.maintenance.find_one({"maintenance_id": maintenance_id})
        if not record:
            return redirect(url_for('maintenance.index'))
            
        new_status = request.form.get('status', 'Completed').strip()
        completion_date = request.form.get('actual_completion', datetime.utcnow().strftime('%Y-%m-%d')).strip()
        remarks = request.form.get('remarks', '').strip()
        condition = request.form.get('condition', 'Good').strip()
        
        asset_id = record.get('asset_id')
        
        update_data = {
            "status": new_status,
            "actual_completion": completion_date if new_status == 'Completed' else None,
            "remarks": remarks or record.get('remarks'),
            "updated_at": get_current_timestamp()
        }
        
        db.maintenance.update_one({"maintenance_id": maintenance_id}, {"$set": update_data})
        
        if new_status == 'Completed':
            db.assets.update_one(
                {"asset_id": asset_id},
                {"$set": {"status": "Available", "condition": condition, "updated_at": get_current_timestamp()}}
            )
            log_asset_history(
                asset_id=asset_id,
                action="Maintenance Completed",
                description=f"Maintenance {maintenance_id} completed. Asset condition: {condition}. Remarks: {remarks}"
            )
        elif new_status == 'Cancelled':
            db.assets.update_one(
                {"asset_id": asset_id},
                {"$set": {"status": "Available", "updated_at": get_current_timestamp()}}
            )
            log_asset_history(
                asset_id=asset_id,
                action="Maintenance Cancelled",
                description=f"Maintenance {maintenance_id} cancelled. Remarks: {remarks}"
            )
            
        return redirect(url_for('maintenance.index'))

    # --------------------------------------------------------------------------
    # AUDIT LOG & ASSET HISTORY ROUTES
    # --------------------------------------------------------------------------
    @app.route('/history', endpoint='history.index')
    @login_required
    def history_index():
        db = get_db()
        action = request.args.get('action', '').strip()
        search = request.args.get('search', '').strip()
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        if page < 1:
            page = 1
            
        query = {}
        if action:
            query["action"] = action
        if search:
            query["$or"] = [
                {"asset_id": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}},
                {"performed_by": {"$regex": search, "$options": "i"}}
            ]
            
        total_logs = db.asset_history.count_documents(query)
        total_pages = max(1, (total_logs + per_page - 1) // per_page)
        if page > total_pages:
            page = total_pages
            
        skip = (page - 1) * per_page
        logs = list(db.asset_history.find(query).sort("timestamp", -1).skip(skip).limit(per_page))
        distinct_actions = db.asset_history.distinct("action")
        
        return render_template(
            'history/index.html',
            logs=logs,
            distinct_actions=distinct_actions,
            selected_action=action,
            search=search,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            total_logs=total_logs
        )

    # --------------------------------------------------------------------------
    # REPORTS & AUDITS ROUTES
    # --------------------------------------------------------------------------
    @app.route('/reports', endpoint='reports.index')
    @login_required
    def reports_index():
        db = get_db()
        
        report_type = request.args.get('report_type', 'all').strip()
        category = request.args.get('category', '').strip()
        status = request.args.get('status', '').strip()
        department = request.args.get('department', '').strip()
        location = request.args.get('location', '').strip()
        
        query = {}
        if report_type == 'available':
            query["status"] = "Available"
        elif report_type == 'assigned':
            query["status"] = "Assigned"
        elif report_type == 'maintenance':
            query["status"] = "Under Maintenance"
        elif report_type == 'damaged':
            query["status"] = "Damaged"
        elif report_type == 'lost':
            query["status"] = "Lost"
        elif report_type == 'retired':
            query["status"] = "Retired"
            
        if category:
            query["category"] = category
        if status and report_type == 'all':
            query["status"] = status
        if department:
            query["department"] = department
        if location:
            query["location"] = location
            
        assets_data = list(db.assets.find(query).sort("asset_id", 1))
        
        total_count = len(assets_data)
        total_val = sum(float(a.get('purchase_cost', 0) or 0) for a in assets_data)
        
        categories = list(db.categories.find().sort("name", 1))
        departments = list(db.departments.find().sort("name", 1))
        locations = list(db.locations.find().sort("name", 1))
        
        return render_template(
            'reports/index.html',
            assets=assets_data,
            report_type=report_type,
            selected_category=category,
            selected_status=status,
            selected_department=department,
            selected_location=location,
            total_count=total_count,
            total_val=total_val,
            total_val_formatted=format_currency(total_val),
            categories=categories,
            departments=departments,
            locations=locations
        )

    # --------------------------------------------------------------------------
    # REST API & REAL-TIME SEARCH ROUTES
    # --------------------------------------------------------------------------
    @app.route('/api/search', endpoint='api.search')
    @login_required
    def api_search():
        q = request.args.get('q', '').strip()
        if not q:
            return jsonify({"results": []})
            
        db = get_db()
        assets = list(db.assets.find({
            "$or": [
                {"asset_id": {"$regex": q, "$options": "i"}},
                {"asset_name": {"$regex": q, "$options": "i"}},
                {"serial_number": {"$regex": q, "$options": "i"}},
                {"brand": {"$regex": q, "$options": "i"}},
                {"model": {"$regex": q, "$options": "i"}},
                {"department": {"$regex": q, "$options": "i"}},
                {"location": {"$regex": q, "$options": "i"}},
                {"assigned_to.name": {"$regex": q, "$options": "i"}}
            ]
        }).limit(8))
        
        results = []
        for a in assets:
            results.append({
                "type": "asset",
                "id": a.get("asset_id"),
                "title": f"{a.get('asset_name')} ({a.get('asset_id')})",
                "subtitle": f"{a.get('category')} • {a.get('location')} • Status: {a.get('status')}",
                "url": f"/assets/view/{a.get('asset_id')}"
            })
            
        return jsonify({"results": results})

    @app.route('/api/dashboard/stats', endpoint='api.dashboard_stats')
    @login_required
    def api_dashboard_stats():
        db = get_db()
        total = db.assets.count_documents({})
        available = db.assets.count_documents({"status": "Available"})
        assigned = db.assets.count_documents({"status": "Assigned"})
        maintenance = db.assets.count_documents({"status": "Under Maintenance"})
        damaged = db.assets.count_documents({"status": "Damaged"})
        lost = db.assets.count_documents({"status": "Lost"})
        retired = db.assets.count_documents({"status": "Retired"})
        
        pipeline = [{"$group": {"_id": None, "total_value": {"$sum": "$purchase_cost"}}}]
        res = list(db.assets.aggregate(pipeline))
        val = res[0]['total_value'] if res else 0
        
        return jsonify({
            "total_assets": total,
            "available_assets": available,
            "assigned_assets": assigned,
            "maintenance_assets": maintenance,
            "damaged_assets": damaged,
            "lost_assets": lost,
            "retired_assets": retired,
            "total_value": val,
            "total_value_formatted": format_currency(val)
        })

    @app.route('/api/assets', methods=['GET'], endpoint='api.get_assets')
    @login_required
    def api_get_assets():
        db = get_db()
        query = {}
        
        status = request.args.get('status')
        if status:
            query['status'] = status
        category = request.args.get('category')
        if category:
            query['category'] = category
        department = request.args.get('department')
        if department:
            query['department'] = department
            
        limit = int(request.args.get('limit', 50))
        assets = list(db.assets.find(query).limit(limit))
        return jsonify({"count": len(assets), "assets": serialize_docs(assets)})

    @app.route('/api/assets/<asset_id>', methods=['GET'], endpoint='api.get_asset')
    @login_required
    def api_get_asset(asset_id):
        db = get_db()
        asset = db.assets.find_one({"asset_id": asset_id})
        if not asset:
            return jsonify({"error": "Asset not found"}), 404
        return jsonify(serialize_doc(asset))

    @app.route('/api/assets', methods=['POST'], endpoint='api.create_asset')
    @login_required
    def api_create_asset():
        data = request.get_json() or request.form.to_dict()
        errors = validate_asset_data(data)
        
        db = get_db()
        serial_number = data.get('serial_number', '').strip()
        if serial_number and db.assets.find_one({"serial_number": serial_number}):
            errors.append(f"Serial number '{serial_number}' already in use.")
            
        if errors:
            return jsonify({"success": False, "errors": errors}), 400
            
        asset_id = generate_next_id('assets', 'AST', 'asset_id', 4)
        now_ts = get_current_timestamp()
        
        new_asset = {
            "asset_id": asset_id,
            "asset_name": data.get('asset_name', '').strip(),
            "category": data.get('category', '').strip(),
            "brand": data.get('brand', '').strip(),
            "model": data.get('model', '').strip(),
            "serial_number": serial_number,
            "purchase_date": data.get('purchase_date', ''),
            "purchase_cost": float(data.get('purchase_cost', 0) or 0),
            "supplier": data.get('supplier', '').strip(),
            "department": data.get('department', '').strip(),
            "location": data.get('location', '').strip(),
            "status": data.get('status', 'Available'),
            "condition": data.get('condition', 'Good'),
            "assigned_to": None,
            "warranty_expiry": data.get('warranty_expiry', ''),
            "description": data.get('description', '').strip(),
            "created_at": now_ts,
            "updated_at": now_ts
        }
        
        db.assets.insert_one(new_asset)
        log_asset_history(
            asset_id=asset_id,
            action="Created",
            description=f"Asset created via API: {new_asset['asset_name']}"
        )
        
        return jsonify({"success": True, "asset": serialize_doc(new_asset)}), 201

    @app.route('/api/assets/<asset_id>', methods=['PUT'], endpoint='api.update_asset')
    @login_required
    def api_update_asset(asset_id):
        db = get_db()
        asset = db.assets.find_one({"asset_id": asset_id})
        if not asset:
            return jsonify({"error": "Asset not found"}), 404
            
        data = request.get_json() or request.form.to_dict()
        errors = validate_asset_data(data, is_update=True)
        
        serial_number = data.get('serial_number', '').strip()
        if serial_number:
            dup = db.assets.find_one({"serial_number": serial_number, "asset_id": {"$ne": asset_id}})
            if dup:
                errors.append(f"Serial number '{serial_number}' already in use.")
                
            if errors:
                return jsonify({"success": False, "errors": errors}), 400
                
        now_ts = get_current_timestamp()
        update_doc = {
            "asset_name": data.get('asset_name', asset.get('asset_name')).strip(),
            "category": data.get('category', asset.get('category')).strip(),
            "brand": data.get('brand', asset.get('brand')).strip(),
            "model": data.get('model', asset.get('model')).strip(),
            "serial_number": serial_number or asset.get('serial_number'),
            "purchase_date": data.get('purchase_date', asset.get('purchase_date')),
            "purchase_cost": float(data.get('purchase_cost', asset.get('purchase_cost', 0)) or 0),
            "supplier": data.get('supplier', asset.get('supplier')).strip(),
            "department": data.get('department', asset.get('department')).strip(),
            "location": data.get('location', asset.get('location')).strip(),
            "status": data.get('status', asset.get('status')),
            "condition": data.get('condition', asset.get('condition')),
            "warranty_expiry": data.get('warranty_expiry', asset.get('warranty_expiry')),
            "description": data.get('description', asset.get('description')).strip(),
            "updated_at": now_ts
        }
        
        db.assets.update_one({"asset_id": asset_id}, {"$set": update_doc})
        log_asset_history(
            asset_id=asset_id,
            action="Updated",
            description="Asset updated via API"
        )
        
        updated_asset = db.assets.find_one({"asset_id": asset_id})
        return jsonify({"success": True, "asset": serialize_doc(updated_asset)})

    @app.route('/api/assets/<asset_id>', methods=['DELETE'], endpoint='api.delete_asset')
    @login_required
    def api_delete_asset(asset_id):
        db = get_db()
        asset = db.assets.find_one({"asset_id": asset_id})
        if not asset:
            return jsonify({"error": "Asset not found"}), 404
            
        log_asset_history(
            asset_id=asset_id,
            action="Deleted",
            description=f"Asset {asset.get('asset_name')} ({asset_id}) deleted via API"
        )
        db.assets.delete_one({"asset_id": asset_id})
        return jsonify({"success": True, "message": f"Asset {asset_id} deleted."})

    @app.route('/api/assets/<asset_id>/assign', methods=['POST'], endpoint='api.api_assign_asset')
    @login_required
    def api_assign_asset(asset_id):
        db = get_db()
        asset = db.assets.find_one({"asset_id": asset_id})
        if not asset:
            return jsonify({"error": "Asset not found"}), 404
            
        data = request.get_json() or request.form.to_dict()
        user_id = data.get('user_id', '').strip()
        user = db.users.find_one({"user_id": user_id})
        if not user:
            return jsonify({"error": "User not found"}), 400
            
        assignment_id = generate_next_id('assignments', 'ASN', 'assignment_id', 4)
        assigned_date = data.get('assigned_date', datetime.utcnow().strftime('%Y-%m-%d'))
        expected_return_date = data.get('expected_return_date')
        dept = data.get('department') or user.get('department')
        
        asn_doc = {
            "assignment_id": assignment_id,
            "asset_id": asset_id,
            "asset_name": asset.get('asset_name'),
            "user_id": user_id,
            "user_name": user.get('name'),
            "user_email": user.get('email'),
            "department": dept,
            "assigned_date": assigned_date,
            "expected_return_date": expected_return_date,
            "status": "Active",
            "notes": data.get('notes', ''),
            "created_at": get_current_timestamp()
        }
        db.assignments.insert_one(asn_doc)
        
        db.assets.update_one(
            {"asset_id": asset_id},
            {"$set": {
                "status": "Assigned",
                "assigned_to": {
                    "user_id": user_id,
                    "name": user.get('name'),
                    "email": user.get('email'),
                    "assignment_date": assigned_date,
                    "assignment_id": assignment_id
                },
                "department": dept,
                "updated_at": get_current_timestamp()
            }}
        )
        
        log_asset_history(
            asset_id=asset_id,
            action="Assigned",
            description=f"Assigned to {user.get('name')} ({user_id}) via API."
        )
        
        return jsonify({"success": True, "assignment": serialize_doc(asn_doc)})

    @app.route('/api/assets/<asset_id>/return', methods=['POST'], endpoint='api.api_return_asset')
    @login_required
    def api_return_asset(asset_id):
        db = get_db()
        asset = db.assets.find_one({"asset_id": asset_id})
        if not asset:
            return jsonify({"error": "Asset not found"}), 404
            
        data = request.get_json() or request.form.to_dict()
        return_date = data.get('return_date', datetime.utcnow().strftime('%Y-%m-%d'))
        condition = data.get('condition', 'Good')
        remarks = data.get('remarks', '')
        
        active_asn = db.assignments.find_one({"asset_id": asset_id, "status": "Active"})
        if active_asn:
            db.assignments.update_one(
                {"_id": active_asn['_id']},
                {"$set": {
                    "status": "Returned",
                    "return_date": return_date,
                    "return_condition": condition,
                    "return_remarks": remarks
                }}
            )
            
        db.assets.update_one(
            {"asset_id": asset_id},
            {"$set": {
                "status": "Available",
                "condition": condition,
                "assigned_to": None,
                "updated_at": get_current_timestamp()
            }}
        )
        
        log_asset_history(
            asset_id=asset_id,
            action="Returned",
            description=f"Asset returned via API. Condition: {condition}. Remarks: {remarks}"
        )
        
        return jsonify({"success": True, "message": f"Asset {asset_id} returned successfully."})

    @app.route('/api/assets/<asset_id>/move', methods=['POST'], endpoint='api.api_move_asset')
    @login_required
    def api_move_asset(asset_id):
        db = get_db()
        asset = db.assets.find_one({"asset_id": asset_id})
        if not asset:
            return jsonify({"error": "Asset not found"}), 404
            
        data = request.get_json() or request.form.to_dict()
        to_location = data.get('to_location', '').strip()
        reason = data.get('reason', 'Location transfer').strip()
        
        if not to_location:
            return jsonify({"error": "to_location is required"}), 400
            
        from_location = asset.get('location', 'Unknown')
        db.assets.update_one(
            {"asset_id": asset_id},
            {"$set": {"location": to_location, "updated_at": get_current_timestamp()}}
        )
        
        log_asset_history(
            asset_id=asset_id,
            action="Moved",
            description=f"Moved from '{from_location}' to '{to_location}'. Reason: {reason}"
        )
        
        return jsonify({"success": True, "from": from_location, "to": to_location})

    @app.route('/api/users', methods=['GET', 'POST'], endpoint='api.api_users')
    @login_required
    def api_users():
        db = get_db()
        if request.method == 'GET':
            users = list(db.users.find().limit(100))
            return jsonify({"users": serialize_docs(users)})
            
        data = request.get_json() or request.form.to_dict()
        errors = validate_user_data(data)
        if errors:
            return jsonify({"success": False, "errors": errors}), 400
            
        email = data.get('email', '').strip()
        if db.users.find_one({"email": email}):
            return jsonify({"success": False, "errors": [f"Email '{email}' is already in use."]}), 400
            
        user_id = generate_next_id('users', 'USR', 'user_id', 3)
        now_ts = get_current_timestamp()
        
        new_user = {
            "user_id": user_id,
            "name": data.get('name', '').strip(),
            "email": email,
            "phone": data.get('phone', '').strip(),
            "department": data.get('department', '').strip(),
            "designation": data.get('designation', 'Staff').strip(),
            "status": data.get('status', 'Active'),
            "created_at": now_ts,
            "updated_at": now_ts
        }
        db.users.insert_one(new_user)
        return jsonify({"success": True, "user": serialize_doc(new_user)}), 201

# Backward-compatibility alias
register_routes = register_all_routes

# ==============================================================================
# 6. APPLICATION FACTORY & LIFECYCLE
# ==============================================================================

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    CORS(app)
    
    # Register all routes directly on app
    register_all_routes(app)
    
    # Register Jinja2 template filters
    app.jinja_env.filters['currency'] = format_currency
    app.jinja_env.filters['date_format'] = format_date
    app.jinja_env.filters['status_badge'] = get_status_badge_class
    app.jinja_env.filters['condition_badge'] = get_condition_badge_class
    
    @app.context_processor
    def inject_globals():
        return {
            'app_title': 'AssetVault',
            'app_subtitle': 'Smart Asset Management System',
            'current_user': get_current_user(),
            'is_authenticated': 'user_id' in session
        }
        
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404
        
    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500
        
    with app.app_context():
        try:
            init_db()
        except Exception as e:
            print(f"Warning: Database initialization deferred or encountered: {e}")
            
    return app

app = create_app()

if __name__ == '__main__':
    print(f"Starting AssetVault on http://127.0.0.1:{Config.APP_PORT}")
    app.run(host='0.0.0.0', port=Config.APP_PORT, debug=Config.DEBUG)