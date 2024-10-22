from flask import Flask, render_template, request, url_for, redirect, session, flash, abort
import pymysql
import requests
from bs4 import BeautifulSoup
from datetime import timedelta

# Database connection
try:
    conn = pymysql.connect(host='localhost', user='root', passwd='guna123', db='searchengine')
    cur = conn.cursor()
except Exception as e:
    print(f"Error connecting to the database: {e}")

app = Flask(__name__)
app.secret_key = 'abcdlsdakf23049'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=3)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login')
def login():
    if session.get('username') is None:
        session.permanent = True
        return render_template('login.html')
    else:
        return redirect(url_for('active'))

@app.route('/logout')
def logout():
    session['username'] = None
    return redirect(url_for("home"))

@app.route('/admin', methods=["POST"])
def authenticate():
    try:
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")
        
        sql = "SELECT * FROM user WHERE Name = %s AND Password = %s"
        cur.execute(sql, (username, password))
        data = cur.fetchone()
        if data is None:
            flash('Incorrect username or password', 'danger')
            return render_template('login.html')
        else:
            session['username'] = username
            flash('Logged in successfully', 'success')
            return redirect(url_for("active"))
    except Exception as e:
        flash(f"An error occurred during authentication: {e}", 'danger')
        return redirect(url_for("login"))

@app.route('/user')
def user():
    try:
        if session.get('username') is None:
            return redirect(url_for("login"))
        else:
            sql = "SELECT * FROM user"
            cur.execute(sql)
            datas = cur.fetchall()
            return render_template('showuser.html', datas=datas)
    except Exception as e:
        flash(f"An error occurred: {e}", 'danger')
        return redirect(url_for("home"))

@app.route('/active')
def active():
    try:
        if session.get('username') is None:
            return redirect(url_for("login"))
        else:
            sql = "SELECT * FROM websites WHERE state=1"
            cur.execute(sql)
            records = cur.fetchall()
            return render_template('active.html', records=records)
    except Exception as e:
        flash(f"An error occurred: {e}", 'danger')
        return redirect(url_for("home"))

@app.route('/deactive')
def deactive():
    try:
        if session.get('username') is None:
            return redirect(url_for("login"))
        else:
            sql = "SELECT * FROM websites WHERE state=0"
            cur.execute(sql)
            records = cur.fetchall()
            return render_template('deactive.html', records=records)
    except Exception as e:
        flash(f"An error occurred: {e}", 'danger')
        return redirect(url_for("home"))

@app.route('/tobedeactivated/<string:id>', methods=["POST", "GET"])
def tobedeactivated(id):
    try:
        if session.get('username') is None:
            return redirect(url_for("login"))
        sql = "UPDATE websites SET state=0 WHERE id=%s"
        cur.execute(sql, (id,))
        conn.commit()
        flash('Website deactivated successfully', 'success')
        return redirect(url_for("deactive"))
    except Exception as e:
        flash(f"An error occurred: {e}", 'danger')
        return redirect(url_for("home"))

@app.route('/tobeactivated/<string:id>', methods=["POST", "GET"])
def tobeactivated(id):
    try:
        if session.get('username') is None:
            return redirect(url_for("login"))
        sql = "UPDATE websites SET state=1 WHERE id=%s"
        cur.execute(sql, (id,))
        conn.commit()
        flash('Website activated successfully', 'success')
        return redirect(url_for("active"))
    except Exception as e:
        flash(f"An error occurred: {e}", 'danger')
        return redirect(url_for("home"))


@app.route('/signup', methods=["POST", "GET"])
def signup():
    if session.get('username') is None:
        return redirect(url_for("login"))

    if request.method == "POST":
        try:
            Name = request.form.get("Name")
            password = request.form.get("Password")
            phoneno = request.form.get("Phoneno")
            Role = request.form.get("Role")
            sql = "INSERT INTO user (Name, Password, Phoneno, Role) VALUES (%s, %s, %s, %s)"
            cur.execute(sql, (Name, password, phoneno, Role))
            conn.commit()
            flash('User registered successfully', 'success')
            return redirect(url_for("login"))
        except Exception as e:
            flash(f"An error occurred: {e}", 'danger')
            return redirect(url_for("signup"))
    
    return render_template('signup.html')


@app.route('/add',methods=["GET","POST"])
def add():
    if session.get('username') == None:
        return redirect(url_for("login"))
    elif request.method =="POST":
        websitename=request.form.get("websitename")
        url_path=request.form.get("url_path")
        discription=request.form.get("discription")
        sql = ("INSERT INTO websites (websitename, url, discription, state) VALUES (%s, %s, %s, %s)")
        cur.connection.ping() #reconnecting mysql
        
        with cur.connection.cursor() as cursor:         
            cursor.execute(sql, (websitename,url_path,discription,True))
            conn.commit()
                                                         
        reqs = requests.get(url_path)
        soup = BeautifulSoup(reqs.text, 'html.parser')
        links=set(soup.find_all('a'))
        for link in links:
            uurl=link.get('href')
            if uurl:
                if uurl.startswith('http'):
                    reque = requests.get(uurl)
                    Soup = BeautifulSoup(reque.text, 'lxml')
                    data={}
                    for tag in ("h1","p","title"):                            
                        data[tag]=Soup.find_all(tag)
                        data[tag]=BeautifulSoup(str(data[tag]),"lxml").text.strip('[]')
                        data[tag]=(" ".join(data[tag].split()))[:3000]
                    if data["h1"]==None or data["p"]==None or data["title"]==None or data["h1"]=="" or data["p"]=="" or data["title"]=="": 
                        print("null")
                    else:
                        print(data['h1'],data['p'],data["title"])
                        sql = ("INSERT INTO metadata (website, url, h1, p, title) VALUES (%s, %s, %s, %s, %s)")
                        cur.execute(sql,(websitename,uurl,data["h1"],data["p"],data["title"]))
                        conn.commit()     
                    
        return redirect(url_for("add"))
    return render_template("add.html")


@app.route('/delete')
def delete():
    try:
        if session.get('username') is None:
            return redirect(url_for("login"))
        else:
            sql = "SELECT * FROM websites"
            cur.execute(sql)
            records = cur.fetchall()
            return render_template('delete.html', records=records)
    except Exception as e:
        flash(f"An error occurred: {e}", 'danger')
        return redirect(url_for("home"))

@app.route('/delete/<string:id>', methods=["POST", "GET"])
def delete_website(id):
    try:
        if session.get('username') is None:
            return redirect(url_for("login"))
        # Find the website name before deleting the website
        cur.execute("SELECT websitename FROM websites WHERE id=%s", (id,))
        website_name = cur.fetchone()[0]
        # Delete related metadata
        sql_metadata = "DELETE FROM metadata WHERE website=%s"
        cur.execute(sql_metadata, (website_name,))
        # Delete the website
        sql_website = "DELETE FROM websites WHERE id=%s"
        cur.execute(sql_website, (id,))
        conn.commit()
        flash('Website deleted successfully', 'success')
        return redirect(url_for("active"))
    except Exception as e:
        flash(f"An error occurred: {e}", 'danger')
        return redirect(url_for("home"))

@app.route('/search', methods=["GET", "POST"])
def search():
    if request.method == "POST":
        search_query = request.form.get('search')
        
        if search_query == "" or search_query is None:
            return redirect(url_for("home"))
        else:
            search_term = "%" + search_query.strip() + "%"
            try:
                # Execute the SQL query only on active websites
                cur.execute('''
                    SELECT m.* FROM metadata m
                    JOIN websites w ON m.website = w.websitename
                    WHERE (m.h1 LIKE %s OR m.p LIKE %s OR m.title LIKE %s) AND w.state=1
                ''', [search_term, search_term, search_term])
                
                datas = cur.fetchall()
                my_data = []
                
                # Process the results
                for item in datas:
                    myitem = []
                    weightage = 0
                    
                    for itemx in item:
                        if isinstance(itemx, str) and search_query.strip().lower() in itemx.lower():
                            weightage += 1
                        myitem.append(itemx)
                    
                    myitem.append(weightage)
                    my_data.append(myitem)
                
                # Sort the data based on weightage
                sorteddata = sorted(my_data, key=lambda x: x[-1], reverse=True)
                return render_template('search.html', datas=sorteddata)

            except Exception as e:
                print(f"An error occurred: {e}")
                return render_template('error.html', message="An error occurred while searching. Please try again later.")

    return render_template('search.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
