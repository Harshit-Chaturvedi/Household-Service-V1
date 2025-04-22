from flask import Flask,render_template, redirect, url_for, request, flash, session, send_from_directory, Response
from flask_migrate import Migrate
from sqlalchemy import or_
from models import db, User, Professional, Service, ServiceRequest
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import base64
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')
import io

app = Flask(__name__)

app.secret_key='Harshit'


UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///A-Z-services.sqlite3"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)

#-----------------------------------SIGN UP ROUTES-----------------------------------------------
@app.route("/customer_signup_form",methods=["GET","POST"])
def customer_signup():
    return render_template("customer_signup.html")

@app.route("/sp_signup_form",methods=["GET","POST"])
def sp_signup():
    services = Service.query.distinct(Service.name).all()
    
    return render_template("service_professional_signup.html", services=services)


@app.route("/c_register", methods=["GET", "POST"])
def C_register():
    if request.method == "POST":
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        phone_number = request.form['phone_number']
        address = request.form['address']
        pincode = request.form['pincode']

        addNew = User(username=username, email=email, password=password, role='customer', phone_number=phone_number, address=address, pin_code=pincode)    
        db.session.add(addNew)
        db.session.commit()

        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return redirect('/customer_signup_form')

@app.route('/sp_register', methods=['POST'])
def sp_register():
  
    email = request.form['email']
    password = request.form['pass']
    username = request.form['username']
    address = request.form['address']
    pincode = request.form['pincode']
    phone_num = request.form['phone_num']
    service_id = request.form['service']

    file = request.files['document']
    
    if file and allowed_file(file.filename):

        filename = secure_filename(file.filename)

        
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

       
        addNew = User(username=username, email=email, password=password, role='professional', phone_number=phone_num, address=address, pin_code=pincode)
        db.session.add(addNew)
        db.session.commit()

 
        user = User.query.filter_by(email=email).first()

       
        service = Service.query.get(service_id)
        if service is None:
            flash("Selected service not found.", "danger")
            return redirect(url_for('sp_register'))
        
        new_professional = Professional(
            user_id=user.id,
            verification_status='pending',
            documents=filename, 
            service=service.name
        )
        db.session.add(new_professional)
        db.session.commit()
        
        flash("Registration successful!", "success")
        return redirect(url_for('login'))

    
    

    flash("Invalid file type. Only PDFs are allowed.", "danger")
    return redirect(url_for('sp_signup_form'))



@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
  
        user = User.query.filter_by(email=email).first()

    
        if user and user.password == password:
            session['user_id'] = user.username  

           
            if user.role == 'customer':
                if user.flagged == 0:

                    return redirect(url_for("customer_dashboard"))
                else:
                    flash('Your account is flagged, you can not login.')
                    return redirect(url_for('login'))

            elif user.role == 'professional':
                professional = Professional.query.filter_by(user_id=user.id).first()

                if professional.verification_status == 'approved':
                    if user.flagged == 0:
                        return redirect(url_for('professional_dashboard'))
                    else:
                        flash('Your account is flagged, you can not login.')
                        return redirect(url_for('login'))


                elif professional.verification_status == 'rejected':
                    flash('Your account is rejected by the admin, you can not login.')
                    return redirect(url_for('login'))
                else:
                    flash('Your account is pending approval from the admin.')
                    return redirect(url_for('login'))

            elif user.role == 'admin':
                return redirect(url_for('Admin_dashboard'))
        else:
            flash('Login failed. Please check your email and password.')
            return redirect(url_for('login'))
    return render_template('login.html')
        
@app.route("/admin", methods=["GET", "POST"])
def Admin_dashboard():
    services = Service.query.all()
    all_sp = Professional.query.filter(or_(Professional.verification_status == 'pending',Professional.verification_status == 'rejected')).all()
    service_requests = ServiceRequest.query.all()
    users_to_flag = User.query.filter(User.role.in_(['customer', 'service_professional'])).all()
    
    approved_sps = Professional.query.filter_by(verification_status="approved").all()
    
    flaggable_users = [
        {"id": user.id, "name": user.username, "role": user.role, "flagged": user.flagged}
        for user in users_to_flag
    ] + [
        {"id": sp.user.id, "name": sp.user.username, "role": "service_professional", "flagged": sp.user.flagged}
        for sp in approved_sps
    ]

    
    return render_template(
        'admin_dashboard.html', 
        services=services, 
        all_sp=all_sp, 
        service_requests=service_requests, 
        flaggable_users=flaggable_users
    )

@app.route("/admin/flag_user/<int:user_id>", methods=["POST"])
def flag_user(user_id):
    user = User.query.get_or_404(user_id)
    user.flagged = True
    db.session.commit()
    flash(f"{user.username} has been flagged.", "success")
    return redirect(url_for('Admin_dashboard'))

@app.route("/admin/unflag_user/<int:user_id>", methods=["POST"])
def unflag_user(user_id):
    user = User.query.get_or_404(user_id)
    user.flagged = False
    db.session.commit()
    flash(f"{user.username} has been unflagged.", "success")
    return redirect(url_for('Admin_dashboard'))

@app.route('/approve_sp/<int:id>', methods=["POST"])
def approve_sp(id):
    sp = Professional.query.get_or_404(id)
    sp.verification_status = "approved"
    db.session.commit()
    flash("Service Professional approved.", "success")
    return redirect(url_for("Admin_dashboard"))

@app.route('/reject_sp/<int:id>', methods=["POST"])
def reject_sp(id):
    sp = Professional.query.get_or_404(id)
    sp.verification_status = "rejected"
    db.session.commit()
    flash("Service Professional rejected.", "danger")
    return redirect(url_for("Admin_dashboard"))



@app.route('/view_document/<filename>')
def view_document(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except FileNotFoundError:
        flash("Document not found.", "danger")
        return redirect(url_for('Admin_dashboard'))



@app.route("/logout",methods=["GET","POST"])
def logout():
    session.pop('logged_in', None)
    return render_template('login.html')

@app.route("/admin_dashboard/new_service", methods=["GET", "POST"])
def new_service():
    if request.method == 'POST':    
        name = request.form['name']
        description = request.form['description']
        base_price = request.form['base_price']
        
        addService = Service(name=name, description=description, base_price=base_price, created_by='admin')
        db.session.add(addService)
        db.session.commit()

        flash('Congratulations, New Service Created!')
        return redirect(url_for('Admin_dashboard'))

    return render_template('new_service.html')

#----------------------Edit and Delete Services--------------------------------------------

@app.route("/admin_dashboard/edit_service/<int:id>", methods=["GET", "POST"])
def edit_service(id):
    service = Service.query.get_or_404(id)

    if request.method == 'POST':
        service.name = request.form['name']
        service.description = request.form['description']
        service.base_price = request.form['base_price']

        db.session.commit()
        flash("Service Updated Successfully!")
        return redirect(url_for('Admin_dashboard'))
    
    return render_template('edit_service.html', service=service)


@app.route("/admin_dashboard/delete_service/<int:id>", methods=["POST"])
def delete_service(id):
    service = Service.query.get_or_404(id)

    db.session.delete(service)
    db.session.commit()
    flash("Service Deleted Successfully!")
    return redirect(url_for('Admin_dashboard'))

@app.route('/admin_dashboard/update_request_status/<int:id>', methods=['POST'])
def update_request_status(id):
    service_request = ServiceRequest.query.get_or_404(id)
    service_request.status = request.form['status']
    db.session.commit()

    flash('Service request status updated!')
    return redirect(url_for('Admin_dashboard'))

@app.route("/admin_search", methods=["GET"])
def admin_search():
    query = request.args.get("search", "").strip()
    if not query:
        flash("Please enter a search term.", "warning")
        return redirect(url_for("Admin_dashboard"))

    services = Service.query.filter(Service.name.ilike(f"%{query}%")).all()
    all_sp = Professional.query.filter(Professional.service.ilike(f"%{query}%")).all()
    service_requests = ServiceRequest.query.filter(ServiceRequest.service.has(Service.name.ilike(f"%{query}%"))).all()

    users_to_flag = User.query.filter(User.role.in_(['customer', 'service_professional'])).all()
    approved_sps = Professional.query.filter_by(verification_status="approved").all()

    flaggable_users = [
        {"id": user.id, "name": user.username, "role": user.role, "flagged": user.flagged}
        for user in users_to_flag
    ] + [
        {"id": sp.user.id, "name": sp.user.username, "role": "service_professional", "flagged": sp.user.flagged}
        for sp in approved_sps
    ]

    return render_template(
        "admin_search.html",
        query=query,
        services=services,
        all_sp=all_sp,
        service_requests=service_requests,
        flaggable_users=flaggable_users
    )



@app.route('/customer_search', methods=['GET'])
def customer_search():
    query = request.args.get('query')
    username = session.get('user.id')
    
    if query:
        results = Service.query.filter(
            (Service.name.ilike(f"%{query}%")) | (Service.description.ilike(f"%{query}%"))
        ).all()
    else:
        results = []
    
    return render_template('customer_search.html', results=results, query=query, username=username)

@app.route('/sp_search', methods=['GET'])
def sp_search():
    query = request.args.get('query')
    
    username = session.get('user_id')
    user = User.query.filter_by(username=username).first()
    professional = Professional.query.filter_by(user_id=user.id).first()
    print(professional.id)
    print(username)
    

    service_requests = (
        db.session.query(ServiceRequest)
        .join(User, ServiceRequest.customer_id == User.id)
        .join(Service, ServiceRequest.service_id == Service.id)
        .filter(
            ServiceRequest.professional_id == professional.id,  
            
            (Service.name.ilike(f"%{query}%") | 
             User.address.ilike(f"%{query}%") | 
             User.pin_code.ilike(f"%{query}%"))
        )
        .all()
    )
    print(service_requests)

    locations = [
        {
            "customer": request.customer,
            "service": request.service,
            "request_date": request.request_date
        }
        for request in service_requests if request.customer.address or request.customer.pin_code
    ]

    return render_template('service_professional_search.html', 
                           query=query, 
                           service_requests=service_requests,
                           locations=locations)



    

@app.route('/customer_dashboard', methods=['GET', 'POST'])
def customer_dashboard():
    subquery = (
        db.session.query(func.min(Service.id).label("id"))
        .group_by(Service.name)
        .subquery()
    )
    services = db.session.query(Service).join(subquery, Service.id == subquery.c.id).all()

    print(services)
    
    username = session.get('user_id')
    user = User.query.filter_by(username=username).first()
    customer_id = user.id  
    service_history = ServiceRequest.query.filter_by(customer_id=customer_id).all()
    
    return render_template('customer_dashboard.html', services=services, service_history=service_history)

@app.route('/service/<int:service_id>')
def service_details(service_id):
    service = Service.query.get_or_404(service_id)
    related_services = Service.query.filter_by(name=service.name).all()
    return render_template('service_details.html', service=service, related_services=related_services)

@app.route('/book_service', methods=['POST'])
def book_service():
    service_id = request.form.get('service_id')
    username = session.get('user_id')
    user = User.query.filter_by(username = username).first()

    customer_id = user.id 
    service = Service.query.get_or_404(service_id)
    request_date = datetime.utcnow()

    new_request = ServiceRequest(
        customer_id=customer_id,
        service_id=service.id,
        request_date=request_date,
        status='Pending'
    )
    db.session.add(new_request)
    db.session.commit()

    professionals = Professional.query.filter_by(service=service.name).all()
    for professional in professionals:
        print(f"Notification sent to {professional.user.username}")

    flash('Service booked successfully!', 'success')
    return redirect(url_for('customer_dashboard'))



@app.route('/edit_service_request/<int:request_id>', methods=['GET', 'POST'])
def edit_service_request(request_id):
    service_request = ServiceRequest.query.get_or_404(request_id)

    if request.method == 'POST':
        if service_request.status == 'In Progress':
            req = request.form['status']
            if(req == 'Completed'):
                service_request.completion_date = datetime.utcnow()
            
            service_request.status = request.form['status']
            service_request.rating = int(request.form['rating'])
            service_request.feedback = request.form['feedback']
            
            db.session.commit()
            flash('Service request updated successfully.', 'success')
            return redirect(url_for('customer_dashboard'))
        else:
            flash('Only "In Progress" requests can be edited.', 'danger')
            return redirect(url_for('customer_dashboard'))

    return render_template('edit_service_request.html', request=service_request)



@app.route('/professional_dashboard')
def professional_dashboard():
    username = session.get('user_id')
    user = User.query.filter_by(username=username).first()
    professional = Professional.query.filter_by(user_id=user.id).first()

    professional_service_name = professional.service

    requests = ServiceRequest.query.join(Service).join(User, ServiceRequest.customer_id == User.id).filter(
    ServiceRequest.professional_id == None,
    professional_service_name == Service.name,
    User.flagged == 0
    ).all()

    closed_requests = ServiceRequest.query.join(User, ServiceRequest.customer_id == User.id).filter(
        ServiceRequest.professional_id == professional.id,
        ServiceRequest.status.in_(['In Progress', 'Completed']),
        User.flagged == 0  
    ).all()

    return render_template('service_professional_dashboard.html', 
                           requests=requests, 
                           closed_requests=closed_requests, 
                           professional=professional)


@app.route('/accept_request', methods=['POST'])
def accept_request():
    request_id = request.form.get('request_id')
    username = session.get('user_id')
    user = User.query.filter_by(username=username).first()
    professional = Professional.query.filter_by(user_id=user.id).first()

    service_request = ServiceRequest.query.get_or_404(request_id)
    
    if service_request.status == 'Pending' and service_request.professional_id is None:
        service_request.professional_id = professional.id
        service_request.status = 'In Progress'
        db.session.commit()
        flash('You have accepted the request.', 'success')
    else:
        flash('This request is no longer available.', 'danger')

    return redirect(url_for('professional_dashboard'))



@app.route('/complete_request', methods=['POST'])
def complete_request():
    request_id = request.form.get('request_id')
    service_request = ServiceRequest.query.get_or_404(request_id)

    username = session.get('user_id')
    user = User.query.filter_by(username=username).first()
    professional = Professional.query.filter_by(user_id=user.id).first()

    if service_request.professional_id == professional.id:
        service_request.status = 'Completed'
        service_request.completion_date = datetime.utcnow()  
        db.session.commit()
        flash('Service marked as completed.', 'success')
    else:
        flash('You cannot complete this service.', 'danger')

    return redirect(url_for('professional_dashboard'))


@app.route('/customer/profile')
def customer_profile():
    username = session.get('user_id')
    user = User.query.filter_by(username=username).first()
    if not user.id:
        return redirect(url_for('login'))
    
    customer = User.query.filter_by(id=user.id, role='customer').first()
    if not customer:
        return "Customer not found", 404
    
    service_history = ServiceRequest.query.filter_by(customer_id=user.id).all()
    return render_template('customer_profile.html', customer=customer, service_history=service_history)

@app.route('/customer/profile/edit', methods=['GET', 'POST'])
def edit_customer_profile():
    username = session.get('user_id')
    user = User.query.filter_by(username=username).first()
    if not user.id:
        return redirect(url_for('login'))
    
    customer = User.query.filter_by(id=user.id, role='customer').first()
    if not customer:
        return "Customer not found", 404
    
    if request.method == 'POST':
        customer.username = request.form['username']
        customer.email = request.form['email']
        customer.phone_number = request.form['phone_number']
        customer.address = request.form['address']
        customer.pin_code = request.form['pin_code']
        
        db.session.commit()
        return redirect(url_for('customer_profile'))
    
    return render_template('edit_customer_profile.html', customer=customer)

@app.route('/professional/profile')
def professional_profile():
    username = session.get('user_id')
    user = User.query.filter_by(username=username).first()
    if not user.id:
        return redirect(url_for('login'))
    
    professional = Professional.query.filter_by(user_id=user.id).first()
    if not professional:
        return "Professional profile not found", 404
    return render_template('service_professional_profile.html', professional=professional)

@app.route('/professional/profile/edit', methods=['GET', 'POST'])
def edit_professional_profile():
    username = session.get('user_id')
    user = User.query.filter_by(username=username).first()

    if not user.id:
        return redirect(url_for('login'))
    
    professional = Professional.query.filter_by(user_id=user.id).first()
    if not professional:
        return "Professional profile not found", 404
    
    if request.method == 'POST':
        professional.user.username = request.form['username']
        professional.user.email = request.form['email']
        professional.user.phone_number = request.form['phone_number']
        professional.user.address = request.form['address']
        professional.service = request.form['service']
        professional.documents = request.form['documents']
        
        db.session.commit()
        return redirect(url_for('professional_profile'))
    
    return render_template('edit_service_professional_profile.html', professional=professional)


@app.route('/sp_summary')
def sp_summary():
    username = session.get('user_id')
    user = User.query.filter_by(username=username).first()
    if not user:
        return redirect(url_for('login'))
    
    professional = Professional.query.filter_by(user_id=user.id).first()
    
    if not professional:
        return "Professional profile not found", 404
    
    total_requests = ServiceRequest.query.filter_by(professional_id=professional.id).count()
    completed_requests = ServiceRequest.query.filter_by(professional_id=professional.id, status='Completed').count()
    pending_requests = ServiceRequest.query.join(Service).filter(
        ServiceRequest.professional_id == None,
        Service.name == professional.service
    ).all()
    pending_requests = len(pending_requests)
    in_progress_requests = ServiceRequest.query.filter_by(professional_id=professional.id, status='In Progress').count()

    if not total_requests:
        return render_template('service_professional_summary.html', service_chart=None)
    

    ratings = ServiceRequest.query.filter_by(professional_id=professional.id).with_entities(ServiceRequest.rating).all()
    rating_counts = {i: 0 for i in range(1, 6)}
    for rating in ratings:
        if rating[0]:  # Ignore null ratings
            rating_counts[rating[0]] += 1

    fig1, ax1 = plt.subplots()
    ax1.bar(
        ['Total', 'Completed', 'Pending', 'In Progress'],
        [total_requests, completed_requests, pending_requests, in_progress_requests],
        color=['blue', 'green', 'orange', 'red']
    )
    ax1.set_title('Service Request Overview')
    ax1.set_ylabel('Count')
    buf1 = io.BytesIO()
    plt.savefig(buf1, format='png')
    buf1.seek(0)
    service_chart = base64.b64encode(buf1.getvalue()).decode('utf-8')
    buf1.close()

    fig2, ax2 = plt.subplots()
    ax2.pie(
        rating_counts.values(),
        labels=[f"{key} Stars" for key in rating_counts.keys()],
        autopct='%1.1f%%',
        startangle=90,
        colors=['gold', 'lightgreen', 'cyan', 'blue', 'purple']
    )
    ax2.set_title('Ratings Distribution')
    buf2 = io.BytesIO()
    plt.savefig(buf2, format='png')
    buf2.seek(0)
    ratings_chart = base64.b64encode(buf2.getvalue()).decode('utf-8')
    buf2.close()

    return render_template('service_professional_summary.html', service_chart=service_chart, ratings_chart=ratings_chart)

@app.route('/customer/summary')
def customer_summary():
    username = session.get('user_id')
    user = User.query.filter_by(username=username).first()  
    service_requests = ServiceRequest.query.filter_by(customer_id=user.id).all()

    if not service_requests:
        return render_template('customer_summary.html', chart_data=None)

    requested_count = sum(1 for req in service_requests if req.status == 'Pending')
    closed_count = sum(1 for req in service_requests if req.status == 'Completed')
    assigned_count = sum(1 for req in service_requests if req.status == 'In Progress')

    fig, ax = plt.subplots(figsize=(6, 4))
    statuses = ['Requested', 'Closed', 'Assigned']
    counts = [requested_count, closed_count, assigned_count]
    colors = ['#4DAF4A', '#377EB8', '#FF7F00']

    ax.bar(statuses, counts, color=colors)
    ax.set_title('Service Requests Summary')
    ax.set_ylabel('Number of Requests')
    ax.set_xlabel('Status')

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    chart_data = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()

    return render_template('customer_summary.html', chart_data=chart_data)


from sqlalchemy import func

@app.route('/admin_summary')
def admin_summary():
    return render_template("admin_summary.html")

@app.route('/summary_chart/<chart_type>')
def summary_chart(chart_type):
    if chart_type == 'overall_ratings':
        data = (
            db.session.query(
                ServiceRequest.professional_id,
                db.func.avg(ServiceRequest.rating).label('average_rating')
            )
            .filter(ServiceRequest.rating.isnot(None)) 
            .group_by(ServiceRequest.professional_id)
            .all()
        )

        if data:
            sp_ids = [f'SP {sp_id}' for sp_id, _ in data] 
            avg_ratings = [avg for _, avg in data] 

            plt.figure(figsize=(5, 3))
            plt.bar(sp_ids, avg_ratings, color='skyblue')
            plt.xlabel('Service Professional (SP ID)')
            plt.ylabel('Average Rating')
            plt.title('')
            plt.xticks(rotation=45)  
            plt.ylim(0, 5)  
            
            plt.show()
        else:
            print("No ratings available for service professionals.")


    elif chart_type == 'requests':
        data = (
            db.session.query(ServiceRequest.status, db.func.count(ServiceRequest.id))
            .group_by(ServiceRequest.status)
            .all()
        )
        labels, values = zip(*data) if data else ([], [])

        plt.figure(figsize=(5, 3))
        plt.bar(labels, values, color=['#4CAF50', '#2196F3', '#FF5722'])
        plt.title('')
        plt.xlabel('Request Status')
        plt.ylabel('Count')
        plt.xticks(rotation=30)

    else:
        return "Invalid chart type", 400

    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    plt.close()
    img.seek(0)
    return Response(img, mimetype='image/png')



if __name__ == '__main__':
    app.debug = True
    app.run()

