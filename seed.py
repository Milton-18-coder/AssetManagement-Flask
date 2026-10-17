"""
AssetVault - Database Seeding Script
Populates realistic sample data for categories, departments, locations, users, assets, assignments, maintenance, and audit history.
"""

from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from app import get_db, init_db, Config

def seed_database():
    db = get_db()
    print("Initializing collections and indexes...")
    init_db()

    print("Clearing existing data for a fresh seed...")
    db.categories.delete_many({})
    db.departments.delete_many({})
    db.locations.delete_many({})
    db.users.delete_many({})
    db.assets.delete_many({})
    db.assignments.delete_many({})
    db.maintenance.delete_many({})
    db.asset_history.delete_many({})

    # 1. Categories
    categories = [
        {"name": "Laptop", "description": "Portable computing devices"},
        {"name": "Desktop", "description": "Fixed workstation computers"},
        {"name": "Monitor", "description": "High-resolution display panels"},
        {"name": "Printer", "description": "Laser and multi-function printers"},
        {"name": "Projector", "description": "Presentation and auditorium projectors"},
        {"name": "Furniture", "description": "Desks, ergonomic chairs, and lab tables"},
        {"name": "Networking", "description": "Switches, routers, and access points"},
        {"name": "Laboratory Equipment", "description": "Oscilloscopes, analyzers, and sensor kits"},
        {"name": "Server", "description": "Rack servers and storage nodes"}
    ]
    db.categories.insert_many(categories)
    print(f"Inserted {len(categories)} categories.")

    # 2. Departments
    departments = [
        {"name": "Computer Science", "head": "Dr. Robert Vance", "email": "cs@assetvault.internal", "location": "Academic Block A", "description": "Computing and Software Engineering Division"},
        {"name": "Information Technology", "head": "Prof. Elena Rostova", "email": "it@assetvault.internal", "location": "Academic Block B", "description": "Enterprise Systems and Network Infrastructure"},
        {"name": "Electronics & Communication", "head": "Dr. Marcus Chen", "email": "ece@assetvault.internal", "location": "Tech Wing C", "description": "Hardware systems, signal processing, and robotics"},
        {"name": "Administration", "head": "David Miller", "email": "admin-dept@assetvault.internal", "location": "Executive Block", "description": "Central management and operations"},
        {"name": "Central Library", "head": "Emily Watson", "email": "library@assetvault.internal", "location": "Library Building", "description": "Digital archives and reading halls"},
        {"name": "Robotics Laboratory", "head": "Dr. Fiona Gallagher", "email": "robotics@assetvault.internal", "location": "Innovation Hub", "description": "Autonomous systems research"}
    ]
    db.departments.insert_many(departments)
    print(f"Inserted {len(departments)} departments.")

    # 3. Locations
    locations = [
        {"name": "Lab 1", "building": "Academic Block A", "floor": "1st Floor", "room": "A-101", "description": "High-Performance Computing Lab"},
        {"name": "Lab 2", "building": "Academic Block A", "floor": "2nd Floor", "room": "A-204", "description": "Software Development Lab"},
        {"name": "Computer Center", "building": "Academic Block B", "floor": "1st Floor", "room": "CC-01", "description": "Central Campus Workstation Lab"},
        {"name": "Central Library", "building": "Library Building", "floor": "2nd Floor", "room": "LIB-201", "description": "Digital Reference Center"},
        {"name": "Executive Office", "building": "Executive Block", "floor": "3rd Floor", "room": "EX-301", "description": "Dean & Management Suites"},
        {"name": "Store Room", "building": "Central Warehouse", "floor": "Basement", "room": "STR-04", "description": "Secure Hardware Inventory & Spares"},
        {"name": "Server Room", "building": "Tech Wing C", "floor": "Ground Floor", "room": "SRV-01", "description": "Climate-controlled server facility"}
    ]
    db.locations.insert_many(locations)
    print(f"Inserted {len(locations)} locations.")

    # 4. Users
    now_str = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    users = [
        {
            "user_id": "USR-001",
            "name": "Dr. Robert Vance",
            "email": "robert.vance@assetvault.internal",
            "phone": "+91 98765 43210",
            "department": "Computer Science",
            "designation": "Professor & Head",
            "status": "Active",
            "created_at": now_str,
            "updated_at": now_str
        },
        {
            "user_id": "USR-002",
            "name": "Sarah Jenkins",
            "email": "sarah.jenkins@assetvault.internal",
            "phone": "+91 98450 11223",
            "department": "Information Technology",
            "designation": "Lead Software Engineer",
            "status": "Active",
            "created_at": now_str,
            "updated_at": now_str
        },
        {
            "user_id": "USR-003",
            "name": "Marcus Chen",
            "email": "marcus.chen@assetvault.internal",
            "phone": "+91 97110 55443",
            "department": "Electronics & Communication",
            "designation": "Senior Researcher",
            "status": "Active",
            "created_at": now_str,
            "updated_at": now_str
        },
        {
            "user_id": "USR-004",
            "name": "Emily Watson",
            "email": "emily.watson@assetvault.internal",
            "phone": "+91 99001 88776",
            "department": "Central Library",
            "designation": "Chief Librarian",
            "status": "Active",
            "created_at": now_str,
            "updated_at": now_str
        },
        {
            "user_id": "USR-005",
            "name": "David Miller",
            "email": "david.miller@assetvault.internal",
            "phone": "+91 98112 33445",
            "department": "Administration",
            "designation": "Operations Director",
            "status": "Active",
            "created_at": now_str,
            "updated_at": now_str
        },
        {
            "user_id": "USR-006",
            "name": "Alex Rivera",
            "email": "alex.rivera@assetvault.internal",
            "phone": "+91 96554 22110",
            "department": "Computer Science",
            "designation": "Graduate Research Scholar",
            "status": "Active",
            "created_at": now_str,
            "updated_at": now_str
        }
    ]
    db.users.insert_many(users)
    print(f"Inserted {len(users)} users.")

    # 5. Assets (18 comprehensive assets)
    today = datetime.utcnow()
    
    assets = [
        {
            "asset_id": "AST-0001",
            "asset_name": "Dell Latitude 5420",
            "category": "Laptop",
            "brand": "Dell",
            "model": "Latitude 5420",
            "serial_number": "DL5420-001",
            "purchase_date": "2024-01-15",
            "purchase_cost": 65000.0,
            "supplier": "ABC Technologies",
            "department": "Computer Science",
            "location": "Lab 1",
            "status": "Assigned",
            "condition": "Good",
            "assigned_to": {
                "user_id": "USR-001",
                "name": "Dr. Robert Vance",
                "email": "robert.vance@assetvault.internal",
                "assignment_date": "2024-02-01",
                "assignment_id": "ASN-0001"
            },
            "warranty_expiry": "2027-01-15",
            "description": "Faculty development laptop configured with Ubuntu LTS and Docker.",
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-02-01T11:00:00Z"
        },
        {
            "asset_id": "AST-0002",
            "asset_name": "MacBook Pro 16 M3 Pro",
            "category": "Laptop",
            "brand": "Apple",
            "model": "MacBook Pro 16",
            "serial_number": "APMBP16-092",
            "purchase_date": "2024-03-10",
            "purchase_cost": 249900.0,
            "supplier": "Imagine Apple Reseller",
            "department": "Information Technology",
            "location": "Computer Center",
            "status": "Assigned",
            "condition": "Excellent",
            "assigned_to": {
                "user_id": "USR-002",
                "name": "Sarah Jenkins",
                "email": "sarah.jenkins@assetvault.internal",
                "assignment_date": "2024-03-15",
                "assignment_id": "ASN-0002"
            },
            "warranty_expiry": "2027-03-10",
            "description": "Lead developer workstation for iOS and cloud deployment.",
            "created_at": "2024-03-10T09:30:00Z",
            "updated_at": "2024-03-15T10:00:00Z"
        },
        {
            "asset_id": "AST-0003",
            "asset_name": "Lenovo ThinkStation P360",
            "category": "Desktop",
            "brand": "Lenovo",
            "model": "ThinkStation P360 Tower",
            "serial_number": "LNTP360-108",
            "purchase_date": "2023-11-20",
            "purchase_cost": 115000.0,
            "supplier": "Lenovo India Enterprise",
            "department": "Computer Science",
            "location": "Lab 1",
            "status": "Available",
            "condition": "Good",
            "assigned_to": None,
            "warranty_expiry": "2026-11-20",
            "description": "Heavy compute desktop workstation with Intel i9 and RTX 3070.",
            "created_at": "2023-11-20T14:20:00Z",
            "updated_at": "2023-11-20T14:20:00Z"
        },
        {
            "asset_id": "AST-0004",
            "asset_name": "HP EliteDesk 800 G9",
            "category": "Desktop",
            "brand": "HP",
            "model": "EliteDesk 800 G9 SFF",
            "serial_number": "HPED800-441",
            "purchase_date": "2023-08-05",
            "purchase_cost": 72000.0,
            "supplier": "Frontline Systems",
            "department": "Administration",
            "location": "Executive Office",
            "status": "Assigned",
            "condition": "Good",
            "assigned_to": {
                "user_id": "USR-005",
                "name": "David Miller",
                "email": "david.miller@assetvault.internal",
                "assignment_date": "2023-08-10",
                "assignment_id": "ASN-0003"
            },
            "warranty_expiry": "2026-08-05",
            "description": "Executive operations administrative system.",
            "created_at": "2023-08-05T11:00:00Z",
            "updated_at": "2023-08-10T12:00:00Z"
        },
        {
            "asset_id": "AST-0005",
            "asset_name": "Dell UltraSharp 27 4K Monitor",
            "category": "Monitor",
            "brand": "Dell",
            "model": "U2723QE",
            "serial_number": "DLU2723-559",
            "purchase_date": "2024-02-12",
            "purchase_cost": 48500.0,
            "supplier": "ABC Technologies",
            "department": "Information Technology",
            "location": "Computer Center",
            "status": "Assigned",
            "condition": "Excellent",
            "assigned_to": {
                "user_id": "USR-002",
                "name": "Sarah Jenkins",
                "email": "sarah.jenkins@assetvault.internal",
                "assignment_date": "2024-03-15",
                "assignment_id": "ASN-0004"
            },
            "warranty_expiry": "2027-02-12",
            "description": "Color-accurate 4K USB-C Hub Monitor for UI/UX development.",
            "created_at": "2024-02-12T10:00:00Z",
            "updated_at": "2024-03-15T10:00:00Z"
        },
        {
            "asset_id": "AST-0006",
            "asset_name": "HP LaserJet Pro MFP M428fdw",
            "category": "Printer",
            "brand": "HP",
            "model": "MFP M428fdw",
            "serial_number": "HPLJ428-903",
            "purchase_date": "2023-05-18",
            "purchase_cost": 42000.0,
            "supplier": "Office Solutions Pvt Ltd",
            "department": "Central Library",
            "location": "Central Library",
            "status": "Available",
            "condition": "Good",
            "assigned_to": None,
            "warranty_expiry": "2026-05-18",
            "description": "Network multifunction monochrome printer and scanner.",
            "created_at": "2023-05-18T08:30:00Z",
            "updated_at": "2023-05-18T08:30:00Z"
        },
        {
            "asset_id": "AST-0007",
            "asset_name": "Epson EB-2250U Full HD Projector",
            "category": "Projector",
            "brand": "Epson",
            "model": "EB-2250U",
            "serial_number": "EPEB225-771",
            "purchase_date": "2023-09-01",
            "purchase_cost": 89000.0,
            "supplier": "AV Solutions Direct",
            "department": "Computer Science",
            "location": "Lab 1",
            "status": "Under Maintenance",
            "condition": "Fair",
            "assigned_to": None,
            "warranty_expiry": "2026-09-01",
            "description": "5,000 lumens high brightness presentation projector.",
            "created_at": "2023-09-01T15:00:00Z",
            "updated_at": "2024-04-10T11:00:00Z"
        },
        {
            "asset_id": "AST-0008",
            "asset_name": "Cisco Catalyst 9300 48-Port Switch",
            "category": "Networking",
            "brand": "Cisco",
            "model": "C9300-48P",
            "serial_number": "CS9300-1123",
            "purchase_date": "2023-02-14",
            "purchase_cost": 310000.0,
            "supplier": "Network Pro Systems",
            "department": "Information Technology",
            "location": "Server Room",
            "status": "Available",
            "condition": "Excellent",
            "assigned_to": None,
            "warranty_expiry": "2028-02-14",
            "description": "Core gigabit PoE+ switch powering academic block WiFi and labs.",
            "created_at": "2023-02-14T09:00:00Z",
            "updated_at": "2023-02-14T09:00:00Z"
        },
        {
            "asset_id": "AST-0009",
            "asset_name": "Tektronix TBS2000B Digital Oscilloscope",
            "category": "Laboratory Equipment",
            "brand": "Tektronix",
            "model": "TBS2104B 100MHz",
            "serial_number": "TK2000-884",
            "purchase_date": "2023-06-25",
            "purchase_cost": 125000.0,
            "supplier": "Scientific Test Instruments",
            "department": "Electronics & Communication",
            "location": "Lab 2",
            "status": "Assigned",
            "condition": "Good",
            "assigned_to": {
                "user_id": "USR-003",
                "name": "Marcus Chen",
                "email": "marcus.chen@assetvault.internal",
                "assignment_date": "2023-07-01",
                "assignment_id": "ASN-0005"
            },
            "warranty_expiry": "2026-06-25",
            "description": "4-channel high precision oscilloscope for embedded system validation.",
            "created_at": "2023-06-25T11:30:00Z",
            "updated_at": "2023-07-01T12:00:00Z"
        },
        {
            "asset_id": "AST-0010",
            "asset_name": "Dell PowerEdge R750 Server",
            "category": "Server",
            "brand": "Dell",
            "model": "PowerEdge R750 2U",
            "serial_number": "DLPE750-009",
            "purchase_date": "2023-04-10",
            "purchase_cost": 540000.0,
            "supplier": "ABC Technologies",
            "department": "Information Technology",
            "location": "Server Room",
            "status": "Available",
            "condition": "Excellent",
            "assigned_to": None,
            "warranty_expiry": "2028-04-10",
            "description": "Dual Intel Xeon Gold, 256GB RAM, VMware ESXi Cluster node.",
            "created_at": "2023-04-10T10:00:00Z",
            "updated_at": "2023-04-10T10:00:00Z"
        },
        {
            "asset_id": "AST-0011",
            "asset_name": "Herman Miller Aeron Ergonomic Chair",
            "category": "Furniture",
            "brand": "Herman Miller",
            "model": "Aeron Size B",
            "serial_number": "HM-AERON-302",
            "purchase_date": "2022-10-15",
            "purchase_cost": 98000.0,
            "supplier": "Workspace Designs",
            "department": "Administration",
            "location": "Executive Office",
            "status": "Available",
            "condition": "Good",
            "assigned_to": None,
            "warranty_expiry": "2034-10-15",
            "description": "Ergonomic executive posturefit mesh chair.",
            "created_at": "2022-10-15T09:00:00Z",
            "updated_at": "2022-10-15T09:00:00Z"
        },
        {
            "asset_id": "AST-0012",
            "asset_name": "Apple iPad Pro 12.9 M2",
            "category": "Laptop",
            "brand": "Apple",
            "model": "iPad Pro 12.9 256GB",
            "serial_number": "APIPAD-4412",
            "purchase_date": "2023-07-20",
            "purchase_cost": 112000.0,
            "supplier": "Imagine Apple Reseller",
            "department": "Central Library",
            "location": "Central Library",
            "status": "Assigned",
            "condition": "Good",
            "assigned_to": {
                "user_id": "USR-004",
                "name": "Emily Watson",
                "email": "emily.watson@assetvault.internal",
                "assignment_date": "2023-08-01",
                "assignment_id": "ASN-0006"
            },
            "warranty_expiry": "2026-07-20",
            "description": "Digital library kiosk administration tablet with Apple Pencil.",
            "created_at": "2023-07-20T10:00:00Z",
            "updated_at": "2023-08-01T11:00:00Z"
        },
        {
            "asset_id": "AST-0013",
            "asset_name": "Lenovo ThinkPad X1 Carbon Gen 11",
            "category": "Laptop",
            "brand": "Lenovo",
            "model": "X1 Carbon Gen 11",
            "serial_number": "LNX1C-7781",
            "purchase_date": "2024-01-05",
            "purchase_cost": 165000.0,
            "supplier": "Lenovo India Enterprise",
            "department": "Computer Science",
            "location": "Lab 2",
            "status": "Assigned",
            "condition": "Excellent",
            "assigned_to": {
                "user_id": "USR-006",
                "name": "Alex Rivera",
                "email": "alex.rivera@assetvault.internal",
                "assignment_date": "2024-01-10",
                "assignment_id": "ASN-0007"
            },
            "warranty_expiry": "2027-01-05",
            "description": "Ultrabook for thesis development and distributed systems research.",
            "created_at": "2024-01-05T11:00:00Z",
            "updated_at": "2024-01-10T12:00:00Z"
        },
        {
            "asset_id": "AST-0014",
            "asset_name": "BenQ 4K Smart Wireless Projector",
            "category": "Projector",
            "brand": "BenQ",
            "model": "TK850i",
            "serial_number": "BNQTK850-61",
            "purchase_date": "2022-09-12",
            "purchase_cost": 145000.0,
            "supplier": "AV Solutions Direct",
            "department": "Information Technology",
            "location": "Computer Center",
            "status": "Damaged",
            "condition": "Poor",
            "assigned_to": None,
            "warranty_expiry": "2025-09-12",
            "description": "Optical lens cracked during conference relocation. Awaiting insurance inspection.",
            "created_at": "2022-09-12T14:00:00Z",
            "updated_at": "2024-03-01T15:00:00Z"
        },
        {
            "asset_id": "AST-0015",
            "asset_name": "Ubiquiti UniFi 6 Pro Access Point",
            "category": "Networking",
            "brand": "Ubiquiti",
            "model": "U6-Pro",
            "serial_number": "UBU6P-3390",
            "purchase_date": "2023-03-18",
            "purchase_cost": 18500.0,
            "supplier": "Network Pro Systems",
            "department": "Central Library",
            "location": "Central Library",
            "status": "Available",
            "condition": "Good",
            "assigned_to": None,
            "warranty_expiry": "2026-03-18",
            "description": "WiFi 6 enterprise ceiling AP.",
            "created_at": "2023-03-18T12:00:00Z",
            "updated_at": "2023-03-18T12:00:00Z"
        },
        {
            "asset_id": "AST-0016",
            "asset_name": "Sony Alpha A7 IV Camera Kit",
            "category": "Laboratory Equipment",
            "brand": "Sony",
            "model": "ILCE-7M4 with 24-70mm G Master",
            "serial_number": "SNYA74-9988",
            "purchase_date": "2023-10-02",
            "purchase_cost": 275000.0,
            "supplier": "Camera Center",
            "department": "Robotics Laboratory",
            "location": "Store Room",
            "status": "Lost",
            "condition": "Critical",
            "assigned_to": None,
            "warranty_expiry": "2025-10-02",
            "description": "Computer vision sensor payload reported missing following field testing.",
            "created_at": "2023-10-02T16:00:00Z",
            "updated_at": "2024-02-18T17:00:00Z"
        },
        {
            "asset_id": "AST-0017",
            "asset_name": "HP ProLiant DL380 G7 Server",
            "category": "Server",
            "brand": "HP",
            "model": "DL380 G7",
            "serial_number": "HPDL380-0012",
            "purchase_date": "2016-04-12",
            "purchase_cost": 380000.0,
            "supplier": "HP India",
            "department": "Information Technology",
            "location": "Store Room",
            "status": "Retired",
            "condition": "Fair",
            "assigned_to": None,
            "warranty_expiry": "2019-04-12",
            "description": "Legacy server decommissioned from production workloads.",
            "created_at": "2016-04-12T09:00:00Z",
            "updated_at": "2023-12-01T10:00:00Z"
        },
        {
            "asset_id": "AST-0018",
            "asset_name": "LG DualUp 28 Monitor",
            "category": "Monitor",
            "brand": "LG",
            "model": "28MQ780-B",
            "serial_number": "LG28MQ-1204",
            "purchase_date": "2024-02-28",
            "purchase_cost": 59900.0,
            "supplier": "ABC Technologies",
            "department": "Computer Science",
            "location": "Lab 1",
            "status": "Available",
            "condition": "Excellent",
            "assigned_to": None,
            "warranty_expiry": "2027-02-28",
            "description": "16:18 aspect ratio vertical multitasking monitor with Ergo Stand.",
            "created_at": "2024-02-28T10:00:00Z",
            "updated_at": "2024-02-28T10:00:00Z"
        }
    ]
    db.assets.insert_many(assets)
    print(f"Inserted {len(assets)} assets.")

    # 6. Assignments
    assignments = [
        {
            "assignment_id": "ASN-0001",
            "asset_id": "AST-0001",
            "asset_name": "Dell Latitude 5420",
            "user_id": "USR-001",
            "user_name": "Dr. Robert Vance",
            "user_email": "robert.vance@assetvault.internal",
            "department": "Computer Science",
            "assigned_date": "2024-02-01",
            "expected_return_date": "2026-12-31",
            "return_date": None,
            "status": "Active",
            "notes": "Allocated for academic research and graduate teaching.",
            "created_at": "2024-02-01T11:00:00Z"
        },
        {
            "assignment_id": "ASN-0002",
            "asset_id": "AST-0002",
            "asset_name": "MacBook Pro 16 M3 Pro",
            "user_id": "USR-002",
            "user_name": "Sarah Jenkins",
            "user_email": "sarah.jenkins@assetvault.internal",
            "department": "Information Technology",
            "assigned_date": "2024-03-15",
            "expected_return_date": "2026-12-31",
            "return_date": None,
            "status": "Active",
            "notes": "Assigned for campus portal modernization.",
            "created_at": "2024-03-15T10:00:00Z"
        },
        {
            "assignment_id": "ASN-0003",
            "asset_id": "AST-0004",
            "asset_name": "HP EliteDesk 800 G9",
            "user_id": "USR-005",
            "user_name": "David Miller",
            "user_email": "david.miller@assetvault.internal",
            "department": "Administration",
            "assigned_date": "2023-08-10",
            "expected_return_date": "",
            "return_date": None,
            "status": "Active",
            "notes": "Executive desktop allocation.",
            "created_at": "2023-08-10T12:00:00Z"
        },
        {
            "assignment_id": "ASN-0004",
            "asset_id": "AST-0005",
            "asset_name": "Dell UltraSharp 27 4K Monitor",
            "user_id": "USR-002",
            "user_name": "Sarah Jenkins",
            "user_email": "sarah.jenkins@assetvault.internal",
            "department": "Information Technology",
            "assigned_date": "2024-03-15",
            "expected_return_date": "2026-12-31",
            "return_date": None,
            "status": "Active",
            "notes": "Secondary display for UI workstation.",
            "created_at": "2024-03-15T10:00:00Z"
        },
        {
            "assignment_id": "ASN-0005",
            "asset_id": "AST-0009",
            "asset_name": "Tektronix TBS2000B Digital Oscilloscope",
            "user_id": "USR-003",
            "user_name": "Marcus Chen",
            "user_email": "marcus.chen@assetvault.internal",
            "department": "Electronics & Communication",
            "assigned_date": "2023-07-01",
            "expected_return_date": "2026-06-30",
            "return_date": None,
            "status": "Active",
            "notes": "Robotics hardware signal analysis.",
            "created_at": "2023-07-01T12:00:00Z"
        },
        {
            "assignment_id": "ASN-0006",
            "asset_id": "AST-0012",
            "asset_name": "Apple iPad Pro 12.9 M2",
            "user_id": "USR-004",
            "user_name": "Emily Watson",
            "user_email": "emily.watson@assetvault.internal",
            "department": "Central Library",
            "assigned_date": "2023-08-01",
            "expected_return_date": "2026-08-01",
            "return_date": None,
            "status": "Active",
            "notes": "Library inventory kiosk inspection tool.",
            "created_at": "2023-08-01T11:00:00Z"
        },
        {
            "assignment_id": "ASN-0007",
            "asset_id": "AST-0013",
            "asset_name": "Lenovo ThinkPad X1 Carbon Gen 11",
            "user_id": "USR-006",
            "user_name": "Alex Rivera",
            "user_email": "alex.rivera@assetvault.internal",
            "department": "Computer Science",
            "assigned_date": "2024-01-10",
            "expected_return_date": "2026-10-01",
            "return_date": None,
            "status": "Active",
            "notes": "Graduate fellowship workstation.",
            "created_at": "2024-01-10T12:00:00Z"
        }
    ]
    db.assignments.insert_many(assignments)
    print(f"Inserted {len(assignments)} assignments.")

    # 7. Maintenance Records
    maintenance = [
        {
            "maintenance_id": "MNT-0001",
            "asset_id": "AST-0007",
            "asset_name": "Epson EB-2250U Full HD Projector",
            "maintenance_type": "Corrective / Repair",
            "issue": "Lamp overheating and auto-shutoff",
            "description": "Projector unit shuts down automatically after 15 minutes of operation. Exhaust fan sensor error code E-04.",
            "service_provider": "Epson Authorized Service Center",
            "start_date": "2024-04-10",
            "expected_completion": "2024-04-20",
            "actual_completion": None,
            "cost": 8500.0,
            "status": "In Progress",
            "remarks": "Replacement thermal sensor and filter ordered from distributor.",
            "created_at": "2024-04-10T11:00:00Z"
        },
        {
            "maintenance_id": "MNT-0002",
            "asset_id": "AST-0003",
            "asset_name": "Lenovo ThinkStation P360",
            "maintenance_type": "Preventive",
            "issue": "Annual thermal paste reapplication and dust de-choking",
            "description": "Scheduled preventive servicing for high-compute lab workstation.",
            "service_provider": "Internal IT Team",
            "start_date": "2024-02-05",
            "expected_completion": "2024-02-06",
            "actual_completion": "2024-02-06",
            "cost": 1200.0,
            "status": "Completed",
            "remarks": "Thermal compound reapplied, stress test passed at 68C max under load.",
            "created_at": "2024-02-05T09:00:00Z"
        },
        {
            "maintenance_id": "MNT-0003",
            "asset_id": "AST-0006",
            "asset_name": "HP LaserJet Pro MFP M428fdw",
            "maintenance_type": "Hardware Upgrade",
            "issue": "Duplex roller unit replacement",
            "description": "Paper jam occurring frequently during double-sided booklet printing.",
            "service_provider": "Office Solutions Pvt Ltd",
            "start_date": "2024-01-18",
            "expected_completion": "2024-01-19",
            "actual_completion": "2024-01-19",
            "cost": 3400.0,
            "status": "Completed",
            "remarks": "Installed OEM pickup roller assembly. 500-page test run completed with zero jams.",
            "created_at": "2024-01-18T10:00:00Z"
        }
    ]
    db.maintenance.insert_many(maintenance)
    print(f"Inserted {len(maintenance)} maintenance records.")

    # 8. Asset History Audit Trail
    history_logs = [
        {
            "asset_id": "AST-0001",
            "action": "Created",
            "description": "Asset 'Dell Latitude 5420' registered with ID AST-0001.",
            "performed_by": "admin",
            "timestamp": "2024-01-15T10:00:00Z"
        },
        {
            "asset_id": "AST-0001",
            "action": "Assigned",
            "description": "Assigned to Dr. Robert Vance (USR-001) in Computer Science.",
            "performed_by": "admin",
            "timestamp": "2024-02-01T11:00:00Z"
        },
        {
            "asset_id": "AST-0002",
            "action": "Created",
            "description": "Asset 'MacBook Pro 16 M3 Pro' registered with ID AST-0002.",
            "performed_by": "admin",
            "timestamp": "2024-03-10T09:30:00Z"
        },
        {
            "asset_id": "AST-0002",
            "action": "Assigned",
            "description": "Assigned to Sarah Jenkins (USR-002) in Information Technology.",
            "performed_by": "admin",
            "timestamp": "2024-03-15T10:00:00Z"
        },
        {
            "asset_id": "AST-0003",
            "action": "Created",
            "description": "Asset 'Lenovo ThinkStation P360' registered with ID AST-0003.",
            "performed_by": "admin",
            "timestamp": "2023-11-20T14:20:00Z"
        },
        {
            "asset_id": "AST-0003",
            "action": "Maintenance Started",
            "description": "Maintenance ticket MNT-0002 started (Preventive).",
            "performed_by": "admin",
            "timestamp": "2024-02-05T09:00:00Z"
        },
        {
            "asset_id": "AST-0003",
            "action": "Maintenance Completed",
            "description": "Maintenance MNT-0002 completed. Condition set to Good.",
            "performed_by": "admin",
            "timestamp": "2024-02-06T16:00:00Z"
        },
        {
            "asset_id": "AST-0007",
            "action": "Created",
            "description": "Asset 'Epson EB-2250U Full HD Projector' registered.",
            "performed_by": "admin",
            "timestamp": "2023-09-01T15:00:00Z"
        },
        {
            "asset_id": "AST-0007",
            "action": "Moved",
            "description": "Moved from 'Store Room' to 'Lab 1'. Reason: Lab seminar projection setup",
            "performed_by": "admin",
            "timestamp": "2023-10-10T11:00:00Z"
        },
        {
            "asset_id": "AST-0007",
            "action": "Maintenance Started",
            "description": "Maintenance ticket MNT-0001 started (Corrective / Repair): Lamp overheating and auto-shutoff.",
            "performed_by": "admin",
            "timestamp": "2024-04-10T11:00:00Z"
        },
        {
            "asset_id": "AST-0014",
            "action": "Status Changed",
            "description": "Asset status changed to 'Damaged'. Condition: Poor. Reason: Lens damaged during transfer.",
            "performed_by": "admin",
            "timestamp": "2024-03-01T15:00:00Z"
        },
        {
            "asset_id": "AST-0016",
            "action": "Status Changed",
            "description": "Asset marked as 'Lost' following post-fieldwork audit report.",
            "performed_by": "admin",
            "timestamp": "2024-02-18T17:00:00Z"
        }
    ]
    db.asset_history.insert_many(history_logs)
    print(f"Inserted {len(history_logs)} audit history records.")

    print("\nDatabase seeding completed successfully!")
    print(f"Admin Username: {Config.ADMIN_USERNAME}")
    print(f"Admin Password: {Config.ADMIN_PASSWORD}")
    print("Database: asset_management is ready.")

if __name__ == '__main__':
    seed_database()
