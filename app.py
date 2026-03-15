from flask import Flask, render_template, session, redirect, url_for, request, flash
import mysql.connector
from datetime import datetime
import uuid

app=Flask(__name__)

app.secret_key="Very strong key"
upload_folder='static/uploads'

mydb=mysql.connector.connect(
    host='localhost',
    user='root',
    password='root',
    database='job_portal'
)

@app.route('/')
def home():
    if 'name' in session:
        return redirect(url_for('login'))
    return render_template('index1.html')  #home page

@app.route('/job')
def job():
    return render_template('jobs.html') # job page

@app.route('/signup') # signup page 
def sign():
    return render_template('signup.html')

@app.route('/signup-submit', methods=['POST', 'GET']) #submit credential  of studet and recuriter and also check user if exist or not
def signupsubmit():
    name=request.form.get('name')
    email=request.form.get('email')
    password=request.form.get('password')
    role=request.form.get('role')

    cursor=mydb.cursor(dictionary=True)

    if role=='student':
        query=('select email from student where email=%s')
        cursor.execute(query, (email,))
        stu = cursor.fetchone()
        if stu:
            return "already exists"
        else:
            query='insert into student (name, password, email) values(%s, %s, %s)'
            values=(name, password, email)
            cursor.execute(query, values)
            mydb.commit()
    else:
        query=('select email from recruiter where email=%s')
        cursor.execute(query, (email,))
        rec = cursor.fetchone()
        if rec:
            return "already exists"
        else:
            query='insert into recruiter (name, password, email) values(%s, %s, %s)'
            values=(name, password, email)
            cursor.execute(query, values)
            mydb.commit()
    cursor.close()

    return "Your data submit sucessfully"

@app.route('/login')
def login():
    return render_template("login.html") #login page

@app.route('/login-submit', methods=['POST', 'GET'])
def loginsubmit():
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role')

    cursor = mydb.cursor(dictionary=True)
    
    if role == "student":
        query = "SELECT id, name FROM student WHERE email=%s AND password=%s"
        cursor.execute(query, (email, password))
        stu = cursor.fetchone()
        cursor.close()  # close cursor, not connection
        if stu:
            session['id'] = stu['id']
            session['name'] = stu['name']
            return redirect(url_for('seeker'))
        else:
            return render_template("login.html", credentials="Wrong Credentials!")
    else:  # recruiter
        query = "SELECT id, name FROM recruiter WHERE email=%s AND password=%s"
        cursor.execute(query, (email, password))
        rec = cursor.fetchone()
        cursor.close()  # close cursor, not connection
        if rec:
            session['rec_id'] = rec['id']
            session['rec_name'] = rec['name']
            return redirect(url_for('recruiter'))
        else:
            return render_template("login.html", credentials="Wrong Credentials!")

@app.route('/seeker_dashbaord') #student dashboard
def seeker():
    if 'name' in session:

        #total jobs
        id=session['id']
        cursor=mydb.cursor(dictionary=True)
        query='select COUNT(*) as Totalapply from applications where student_id=%s'
        values=(id,)
        cursor.execute(query, values)
        result=cursor.fetchone()

        # applied jobs
        query2 = """
        SELECT job_post.job_title, job_post.company_name, applications.status
        FROM applications
        JOIN job_post ON applications.job_id = job_post.id
        WHERE applications.student_id=%s
        """
        cursor.execute(query2,(id,))
        jobs = cursor.fetchall()
        
        #accept applications
        query4='select count(*) as acc from applications where student_id=%s and status="Interview"'
        cursor.execute(query4,(id,))
        accept=cursor.fetchone()

        #reject applications
        query3='select count(*) as rej from applications where student_id=%s and status="Rejected"'
        cursor.execute(query3, (id,))
        reject=cursor.fetchone()

        cursor.close()
        return render_template('_dash.html', name=session['name'], Totalapply=result['Totalapply'], jobs=jobs, reject=reject['rej'], Accept=accept['acc'])
    return redirect(url_for('sign'))

@app.route('/recruiter_dashbaord') # recruiter dashboard
def recruiter():
    if 'rec_name' in session:
        rec_id = session['rec_id']
        cursor=mydb.cursor(dictionary=True)

        #total job posts
        query=('select COUNT(*) as total_jobs from job_post where recruiter_id=%s')
        values=(rec_id,)
        cursor.execute(query, values)
        result=cursor.fetchone()

        #total applications, applied by students
        query3 = """
                SELECT COUNT(*) AS cand 
                FROM applications 
                INNER JOIN job_post 
                ON applications.job_id = job_post.id 
                WHERE job_post.recruiter_id = %s
                """

        cursor.execute(query3, (rec_id,))
        candidates = cursor.fetchone()

        #rejected applications
        query4="""
                SELECT COUNT(*) AS reje
                FROM applications
                INNER JOIN job_post 
                ON applications.job_id = job_post.id
                WHERE job_post.recruiter_id = %s
                AND applications.status = 'Rejected';"""
        cursor.execute(query4,(rec_id,))
        rejected=cursor.fetchone()

        #shorlist applications
        query4="""
                SELECT COUNT(*) AS acce
                FROM applications
                INNER JOIN job_post 
                ON applications.job_id = job_post.id
                WHERE job_post.recruiter_id = %s
                AND applications.status = 'Interview';"""
        cursor.execute(query4,(rec_id,))
        accepted=cursor.fetchone()

        
        #recent applied applications
        query2='''SELECT applications.*, student.name, student.email, student.profile, job_post.job_title
                FROM applications
                INNER JOIN student ON applications.student_id = student.id
                INNER JOIN job_post ON applications.job_id = job_post.id
                WHERE job_post.recruiter_id = %s
                ORDER BY applications.id DESC;'''
        values=(rec_id,)
        cursor.execute(query2, (values))
        applications=cursor.fetchall()

        cursor.close()
        return render_template('recruiter.html', name=session.get('rec_name'), accepted=accepted['acce'],Totaljobs=result['total_jobs'], applications=applications, candidates=candidates['cand'], rejected=rejected['reje'])
    return redirect(url_for('login'))

@app.route('/update_status', methods=['POST'])  #update applicaton by recruiter
def update_status():
    if 'rec_name' in session:
        rec_id = session['rec_id']
        application_id = request.form['application_id']
        status = request.form['status']

        cursor = mydb.cursor()

        # Only update if this application belongs to a job posted by this recruiter
        cursor.execute("""
                UPDATE applications a
                INNER JOIN job_post j ON a.job_id = j.id
                SET a.status = %s
                WHERE a.id = %s AND j.recruiter_id = %s
            """, (status, application_id, rec_id))

        mydb.commit()
        cursor.close()

        return redirect(url_for('recruiter'))

    return redirect(url_for('login'))

@app.route('/upload_resume') #upload resume page
def upload_resume():
    if "id" in session:
        return render_template('resume.html')
    
    return redirect(url_for('login'))

@app.route('/submit_resume', methods=['GET', 'POST'])
def submit_resume():          #this is function to upload resume and save in folder
    if "id" in session:
        id=session['id']
        print(id)

        exe = ['.png', '.jpg', '.jpeg', '.webp']

        resume = request.files['resume']
        filename = resume.filename

        if filename.lower().endswith(tuple(exe)):
            
            unique_filename= str(uuid.uuid1())+ "_" +filename
            #
            cursor=mydb.cursor(dictionary=True)
            query='update student set profile=%s where id=%s'
            Values=(unique_filename, id)
            cursor.execute(query, Values)
            resume.save(upload_folder+'/'+unique_filename)
            mydb.commit()
            cursor.close()

        else:
            return render_template('resume.html', wrong='Upload in Image formart only')
        

    return redirect(url_for('upload_resume'))


@app.route('/post_job')
def post_job():
    if 'rec_name' in session:
        return render_template('postjob.html') #job post html page
    return redirect(url_for('login'))

@app.route('/postjob-submit', methods=['GET', 'POST']) #job post backend
def postjob_submit():
    if "rec_id" in session:
        rec_id = session['rec_id']
        job_title = request.form.get('job_title')
        company_name = request.form.get('company_name')
        location = request.form.get('location')
        job_type = request.form.get('job_type')
        experience = request.form.get('experience')
        salary_range = request.form.get('salary_range')
        deadline = request.form.get('deadline')
        skills = request.form.get('skills')
        job_description = request.form.get('job_description')
        website = request.form.get('website')

        cursor = mydb.cursor()
        query='''insert into job_post (recruiter_id, job_title, company_name, location, job_type, experience, salary_range, deadline, skills, job_description, website)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'''
        
        values = (
            rec_id, job_title, company_name, location, job_type,
            experience, salary_range, deadline, skills, job_description, website
        )

        cursor.execute(query, values)
        mydb.commit()
        cursor.close()
        return render_template('postjob.html', success="Posted successfully!")
    

    return redirect(url_for('login'))
        
@app.route('/view_posted_jobs', methods=['GET','POST']) #view job posted by only recruiter 
def view_posted_jobs():
    if "rec_id" in session:
        rec_id=session['rec_id']

        cursor = mydb.cursor(dictionary=True)
        query = "SELECT * FROM job_post WHERE recruiter_id=%s"
        cursor.execute(query, (rec_id,))
        jobs = cursor.fetchall()
        cursor.close()
        return render_template("view_posted_jobs.html", jobs=jobs)

    return redirect(url_for('login'))

@app.route('/job_page') #student can see posted jobs
def jobs():
    if "name" in session:
        cursor=mydb.cursor(dictionary=True)
        query="select * from job_post"
        cursor.execute(query)
        job=cursor.fetchall()
        cursor.close()

        
        return render_template('jobs.html', job=job)
    return redirect(url_for('login'))  

# from flask import Flask, session, redirect, url_for, request, flash
# from datetime import datetime

@app.route('/apply/<int:job_id>', methods=['POST'])
def apply_job(job_id):
    # Make sure student is logged in
    if 'id' not in session:
        flash("Please log in as a student to apply", "error")
        return redirect(url_for('login'))

    student_id = session['id']
    cursor = mydb.cursor(dictionary=True)

    # Check if already applied
    cursor.execute(
        "SELECT * FROM applications WHERE student_id=%s AND job_id=%s",
        (student_id, job_id)
    )
    existing = cursor.fetchone()
    if existing:
        flash("You have already applied for this job!", "error")
    else:
        # Insert new application
        cursor.execute(
            "INSERT INTO applications (student_id, job_id, applied_on) VALUES (%s, %s, %s)",
            (student_id, job_id, datetime.now())
        )
        mydb.commit()
        flash("Applied successfully!", "success")

    return redirect(url_for('jobs'))  # Redirect back to jobs page  

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)