from flask import Flask, render_template, request, url_for, redirect, session, flash, abort
import pymysql
import requests
from bs4 import BeautifulSoup
from datetime import timedelta

# Database connection
try:
    conn = pymysql.connect(host='localhost', user='root', passwd='senthil123', db='searchengine')
    cur = conn.cursor()
except Exception as e:
    print(f"Error connecting to the database: {e}")

app = Flask(__name__)
app.secret_key = 'abcdlsdakf23049'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=3)

class BaseView:
    def __init__(self):
        self.connection = conn
        self.cursor = cur

    def is_logged_in(self):
        return session.get('username') is not None

    def render_template(self, template_name, **context):
        return render_template(template_name, **context)

    def flash_message(self, message, category='info'):
        flash(message, category)

# Inheriting from BaseView for the main app functionality
class AppViews(BaseView):
    @app.route('/')
    def home(self):
        return self.render_template('home.html')

    @app.route('/login')
    def login(self):
        if not self.is_logged_in():
            session.permanent = True
            return self.render_template('login.html')
        else:
            return redirect(url_for('active'))

    @app.route('/logout')
    def logout(self):
        session['username'] = None
        self.flash_message('Logged out successfully', 'info')
        return redirect(url_for("home"))

    @app.route('/admin', methods=["POST"])
    def authenticate(self):
        try:
            if request.method == "POST":
                username = request.form.get("username")
                password = request.form.get("password")
            
            sql = "SELECT * FROM user WHERE Name = %s AND Password = %s"
            self.cursor.execute(sql, (username, password))
            data = self.cursor.fetchone()
            if data is None:
                self.flash_message('Incorrect username or password', 'danger')
                return self.render_template('login.html')
            else:
                session['username'] = username
                self.flash_message('Logged in successfully', 'success')
                return redirect(url_for("active"))
        except Exception as e:
            self.flash_message(f"An error occurred during authentication: {e}", 'danger')
            return redirect(url_for("login"))

    @app.route('/user')
    def user(self):
        if not self.is_logged_in():
            return redirect(url_for("login"))
        else:
            sql = "SELECT * FROM user"
            self.cursor.execute(sql)
            datas = self.cursor.fetchall()
            return self.render_template('showuser.html', datas=datas)

    @app.route('/active')
    def active(self):
        if not self.is_logged_in():
            return redirect(url_for("login"))
        else:
            sql = "SELECT * FROM websites WHERE state=1"
            self.cursor.execute(sql)
            records = self.cursor.fetchall()
            return self.render_template('active.html', records=records)

    @app.route('/deactive')
    def deactive(self):
        if not self.is_logged_in():
            return redirect(url_for("login"))
        else:
            sql = "SELECT * FROM websites WHERE state=0"
            self.cursor.execute(sql)
            records = self.cursor.fetchall()
            return self.render_template('deactive.html', records=records)

    @app.route('/tobedeactivated/<string:id>', methods=["POST", "GET"])
    def tobedeactivated(self, id):
        if not self.is_logged_in():
            return redirect(url_for("login"))
        sql = "UPDATE websites SET state=0 WHERE id=%s"
        self.cursor.execute(sql, (id,))
        self.connection.commit()
        self.flash_message('Website deactivated successfully', 'success')
        return redirect(url_for("deactive"))

    @app.route('/tobeactivated/<string:id>', methods=["POST", "GET"])
    def tobeactivated(self, id):
        if not self.is_logged_in():
            return redirect(url_for("login"))
        sql = "UPDATE websites SET state=1 WHERE id=%s"
        self.cursor.execute(sql, (id,))
        self.connection.commit()
        self.flash_message('Website activated successfully', 'success')
        return redirect(url_for("active"))

    @app.route('/signup', methods=["POST", "GET"])
    def signup(self):
        if not self.is_logged_in():
            return redirect(url_for("login"))

        if request.method == "POST":
            try:
                Name = request.form.get("Name")
                password = request.form.get("Password")
                phoneno = request.form.get("Phoneno")
                Role = request.form.get("Role")
                sql = "INSERT INTO user (Name, Password, Phoneno, Role) VALUES (%s, %s, %s, %s)"
                self.cursor.execute(sql, (Name, password, phoneno, Role))
                self.connection.commit()
                self.flash_message('User registered successfully', 'success')
                return redirect(url_for("login"))
            except Exception as e:
                self.flash_message(f"An error occurred: {e}", 'danger')
                return redirect(url_for("signup"))
        
        return self.render_template('signup.html')

    @app.route('/add', methods=["GET", "POST"])
    def add(self):
        if not self.is_logged_in():
            return redirect(url_for("login"))
        elif request.method == "POST":
            websitename = request.form.get("websitename")
            url_path = request.form.get("url_path")
            discription = request.form.get("discription")
            sql = ("INSERT INTO websites (websitename, url, discription, state) VALUES (%s, %s, %s, %s)")
            self.cursor.connection.ping()  # reconnecting mysql
            
            with self.cursor.connection.cursor() as cursor:         
                cursor.execute(sql, (websitename, url_path, discription, True))
                self.connection.commit()
                                                            
            reqs = requests.get(url_path)
            soup = BeautifulSoup(reqs.text, 'html.parser')
            links = set(soup.find_all('a'))
            for link in links:
                uurl = link.get('href')
                if uurl:
                    if uurl.startswith('http'):
                        reque = requests.get(uurl)
                        Soup = BeautifulSoup(reque.text, 'lxml')
                        data = {}
                        for tag in ("h1", "p", "title"):                            
                            data[tag] = Soup.find_all(tag)
                            data[tag] = BeautifulSoup(str(data[tag]), "lxml").text.strip('[]')
                            data[tag] = (" ".join(data[tag].split()))[:3000]
                        if not all([data["h1"], data["p"], data["title"]]):
                            print("null")
                        else:
                            print(data['h1'], data['p'], data["title"])
                            sql = ("INSERT INTO metadata (website, url, h1, p, title) VALUES (%s, %s, %s, %s, %s)")
                            self.cursor.execute(sql, (websitename, uurl, data["h1"], data["p"], data["title"]))
                            self.connection.commit()     
                        
            return redirect(url_for("add"))
        return self.render_template("add.html")

    @app.route('/delete')
    def delete(self):
        if not self.is_logged_in():
            return redirect(url_for("login"))
        else:
            sql = "SELECT * FROM websites"
            self.cursor.execute(sql)
            records = self.cursor.fetchall()
            return self.render_template('delete.html', records=records)

    @app.route('/delete/<string:id>', methods=["POST", "GET"])
    def delete_website(self, id):
        if not self.is_logged_in():
            return redirect(url_for("login"))
        # Find the website name before deleting the website
        self.cursor.execute("SELECT websitename FROM websites WHERE id=%s", (id,))
        website_name = self.cursor.fetchone()[0]
        # Delete related metadata
        sql_metadata = "DELETE FROM metadata WHERE website=%s"
        self.cursor.execute(sql_metadata, (website_name,))
        # Delete the website
        sql_website = "DELETE FROM websites WHERE id=%s"
        self.cursor.execute(sql_website, (id,))
        self.connection.commit()
        self.flash_message('Website deleted successfully', 'success')
        return redirect(url_for("active"))

    @app.route('/search', methods=["GET", "POST"])
    def search(self):
        if request.method == "POST":
            search_query = request.form.get('search')
            
            if not search_query:
                return redirect(url_for("home"))
            else:
                search_term = "%" + search_query.strip() + "%"
                try:
                    # Execute the SQL query only on active websites
                    self.cursor.execute('''
                        SELECT m.* FROM metadata m
                        JOIN websites w ON m.website = w.websitename
                        WHERE (m.h1 LIKE %s OR m.p LIKE %s OR m.title LIKE %s) AND w.state=1
                    ''', [search_term, search_term, search_term])
                    
                    datas = self.cursor.fetchall()
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
                    return self.render_template('search.html', datas=sorteddata)

                except Exception as e:
                    print(f"An error occurred: {e}")
                    return self.render_template('error.html', message="An error occurred while searching. Please try again later.")

        return self.render_template('search.html')

# Create an instance of AppViews
app_views = AppViews()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
