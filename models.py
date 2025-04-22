from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'service_professional', 'customer'
    phone_number = db.Column(db.String(15))
    address = db.Column(db.String(255))
    pin_code = db.Column(db.String(10))
    flagged = db.Column(db.Boolean, default=False, nullable=False)
    
    services_created = db.relationship('Service', backref='creator', lazy=True)
    professional_profile = db.relationship('Professional', backref='user', uselist=False)
    customer_requests = db.relationship('ServiceRequest', backref='customer', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    base_price = db.Column(db.Float, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  
    
    
    service_requests = db.relationship('ServiceRequest', backref='service', lazy=True)

    def __repr__(self):
        return f'<Service {self.name}>'

class Professional(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  
    verification_status = db.Column(db.String(20), nullable=False)  # 'pending', 'approved', 'rejected'
    service = db.Column(db.String(50))
    documents = db.Column(db.String(255))  
    
    service_requests = db.relationship('ServiceRequest', backref='professional', lazy=True)

    def __repr__(self):
        return f'<Professional {self.user.username}>'   

        
class ServiceRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # FK to User table (Customer)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)  # FK to Service table
    professional_id = db.Column(db.Integer, db.ForeignKey('professional.id'), nullable=True)  # FK to Professional table
    status = db.Column(db.String(20), nullable=False, default='Pending')  # 'Pending', 'In Progress', 'Completed'
    request_date = db.Column(db.DateTime, nullable=False)
    completion_date = db.Column(db.DateTime)
    rating = db.Column(db.Integer)
    feedback = db.Column(db.Text)

    def __repr__(self):
        return f'<ServiceRequest {self.id} - {self.status}>'




