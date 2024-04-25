from flask import Flask, request, make_response, redirect, url_for
from flask_mysqldb import MySQL

"""
Description: This project will act as a way to connect students (previous, current, or future) to track the classes they have taken.
Students sign up with their school email
Students can register for existing or new classes and say the semester they have taken the class.
Users may also search for other individuals who have taken / will take a given class; allowing them to network and collaborate with their peers.
"""

app = Flask(__name__)

app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = "password"
app.config["MYSQL_HOST"] = "127.0.0.1"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"
app.config["MYSQL_PORT"] = 3306
# app.config["MYSQL_DB"] = "cpsc_449"
# app.config["MYSQL_PORT"] = 3307
app.config["MYSQL_DB"] = "cpsc-449"

mysql = MySQL(app)


def response(data, status_code=200):
    """
    Helper function to create a response with the correct headers

    Args:
        data (dict): The data to be returned in the response
        status_code (int): The status code of the response, defaults to 200

    Returns:
        Response: The response object
    """
    response = make_response(data, status_code)
    response.headers["Content-Type"] = "application/json"
    return response


###########################################
# ? DATABASE
###########################################
@app.route("/initialize-db", methods=["POST"])
def initialize_db():
    cur = mysql.connection.cursor()
    # ? drop tables if they exist
    cur.execute("DROP TABLE IF EXISTS enrollments")
    cur.execute("DROP TABLE IF EXISTS students")
    cur.execute("DROP TABLE IF EXISTS classes")

    # ? create tables
    cur.execute(
        "CREATE TABLE students (id INT AUTO_INCREMENT PRIMARY KEY, email VARCHAR(255), full_name VARCHAR(255), grad_year INT)"
    )
    cur.execute(
        "CREATE TABLE classes (id INT AUTO_INCREMENT PRIMARY KEY, subject VARCHAR(255), class_number INT, semester VARCHAR(255), school_year INT, professor VARCHAR(255))"
    )
    cur.execute(
        "CREATE TABLE enrollments (id INT AUTO_INCREMENT PRIMARY KEY, student_id INT, class_id INT)"
    )

    # ? foreign key constraints
    cur.execute(
        "ALTER TABLE enrollments ADD CONSTRAINT fk_student_id FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE"
    )
    cur.execute(
        "ALTER TABLE enrollments ADD CONSTRAINT fk_class_id FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE"
    )

    # ? unique constraints
    cur.execute("ALTER TABLE students ADD CONSTRAINT unique_email UNIQUE (email)")
    cur.execute(
        "ALTER TABLE classes ADD CONSTRAINT unique_class UNIQUE (subject, class_number, semester, school_year, professor)"
    )

    mysql.connection.commit()
    cur.close()
    return response({"msg": "Database Initialized!"})


@app.route("/seed-db", methods=["POST"])
def seed_db():
    cur = mysql.connection.cursor()

    students = [
        ("john@csu.fullerton.edu", "John Smith", 2023),
        ("jane@csu.fullerton.edu", "Jane Smith", 2022),
        ("jack@csu.fullerton.edu", "Jack Smith", 2021),
    ]

    for student in students:
        cur.execute(
            "INSERT INTO students (email, full_name, grad_year) VALUES (%s, %s, %s)",
            student,
        )

    classes = [
        ("CPSC", 349, "Fall", 2021, "Dr. Smith"),
        ("CPSC", 335, "Fall", 2021, "Dr. Smith"),
    ]

    for class_ in classes:
        cur.execute(
            "INSERT INTO classes (subject, class_number, semester, school_year, professor) VALUES (%s, %s, %s, %s, %s)",
            class_,
        )

    enrollments = [
        (1, 1),
        (2, 1),
        (2, 2),
        (3, 2),
    ]
    for enrollment in enrollments:
        cur.execute(
            "INSERT INTO enrollments (student_id, class_id) VALUES (%s, %s)", enrollment
        )

    mysql.connection.commit()
    cur.close()
    return response({"msg": "Database Seeded!"})


###########################################
# ? LOGIN
###########################################
# ! NOT IMPLEMENTED
@app.route("/", methods=["GET"])
def index():
    return redirect(url_for("get_all_classes"))


@app.route("/login", methods=["POST"])
def login():
    return redirect(url_for("index"))


###########################################
# ? STUDENT CRUD
###########################################
@app.route("/student", methods=["POST"])
def create_student():
    fields = ["email", "full_name", "grad_year"]
    for field in fields:
        if field not in request.form:
            return response({"msg": "Fields Missing!"}, 400)
    email = request.form["email"]
    full_name = request.form["full_name"]
    grad_year = request.form["grad_year"]

    # grad year should be an int
    try:
        grad_year = int(grad_year)
    except:
        return response({"msg": "Grad Year must be an integer!"}, 400)

    if email and full_name and grad_year:
        cur = mysql.connection.cursor()

        # check for existing student with that email
        cur.execute("SELECT * FROM students WHERE email = %s", (email,))
        data = cur.fetchone()
        if data:
            res = response({"msg": "A student with that email already exists"}, 409)
        else:
            cur.execute(
                "INSERT INTO students (email, full_name, grad_year) VALUES (%s, %s, %s)",
                (email, full_name, grad_year),
            )
            mysql.connection.commit()
            cur.execute("SELECT * FROM students WHERE email = %s", (email,))
            new_student = cur.fetchone()
            res = response({"msg": "Student Created!", "student": new_student}, 201)
        cur.close()
    else:
        res = response({"msg": "Fields Empty!"}, 422)

    return res


@app.route("/student/<string:email>", methods=["GET"])
def get_student(email: str):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM students WHERE email = %s", (email,))
    data = cur.fetchone()
    if not data:
        res = response({"msg": "Student Not Found!"}, 404)
    else:
        res = response({"student": data})
    cur.close()
    return res


@app.route(
    "/student/subject/<string:subject>/class-number/<int:class_number>", methods=["GET"]
)
def get_students_by_enrollments_in_class(subject: str, class_number: str):
    cur = mysql.connection.cursor()
    # check if class exists
    cur.execute(
        "SELECT * FROM classes WHERE subject = %s AND class_number = %s",
        (subject, class_number),
    )
    class_ = cur.fetchone()
    if not class_:
        res = response({"msg": "Class Not Found!"}, 404)
    else:
        cur.execute(
            "SELECT * FROM students s JOIN enrollments e ON s.id = e.student_id JOIN classes c ON c.id = e.class_id WHERE c.subject = %s AND c.class_number = %s",
            (subject, class_number),
        )
        students = cur.fetchall()
        students = [
            {
                "email": student["email"],
                "full_name": student["full_name"],
                "grad_year": student["grad_year"],
            }
            for student in students
        ]

        res = response({"class": class_, "students": students})

    cur.close()
    return res


@app.route("/student/<string:email>", methods=["PUT"])
def update_student(email: str):
    try:
        request_data = request.get_json()
    except:
        return response({"msg": "No data provided!"}, 400)

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM students WHERE email = %s", (email,))
    student = cur.fetchone()

    if not student:
        res = response({"msg": "Student Not Found!"}, 404)
    else:
        sql_prompt = "UPDATE students SET"
        sql_select = f'SELECT * FROM students WHERE email = "{email}"'
        potential_args = [
            {"sql": "full_name", "value": request_data.get("full_name", None)},
            {"sql": "grad_year", "value": request_data.get("grad_year", None)},
        ]

        arg_count = 0
        for arg in potential_args:
            if arg["value"]:
                if arg_count > 0:
                    sql_prompt += ","
                sql_select += " AND"
                arg_count += 1
                temp = arg["value"]
                if type(arg["value"]) is str:
                    temp = f'"{arg["value"]}"'
                sql_prompt += f" {arg['sql']} = {temp}"
                sql_select += f" {arg['sql']} = {temp}"

        sql_prompt += f' WHERE email = "{email}"'

        if arg_count > 0:
            cur.execute(sql_select)
            data = cur.fetchone()
            if data:
                res = response({"msg": "No changes were made", "student": data})
            else:
                cur.execute(sql_prompt)

                cur.execute("SELECT * FROM students WHERE email = %s", (email,))
                updated_student = cur.fetchone()

                res = response(
                    {"msg": "Student Updated!", "student": updated_student}, 200
                )
        else:
            res = response({"msg": "Fields Missing!"}, 400)
    mysql.connection.commit()
    cur.close()
    return res


@app.route("/student/<string:email>", methods=["DELETE"])
def delete_student(email: str):
    cur = mysql.connection.cursor()

    # check if student exists
    cur.execute("SELECT * FROM students WHERE email = %s", (email,))
    student = cur.fetchone()
    if not student:
        res = response({"msg": "Student Not Found!"}, 404)
    else:
        cur.execute("DELETE FROM students WHERE email = %s", (email,))
        mysql.connection.commit()
        res = response({"msg": "Student Deleted!", "student": student}, 200)
    cur.close()
    return res


##########################################
# ? CLASS CRUD
##########################################
@app.route("/class", methods=["POST"])
def create_class():
    fields = ["subject", "class_number", "semester", "school_year", "professor"]
    for field in fields:
        if field not in request.form:
            return response({"msg": "Fields Missing!"}, 400)
    subject = request.form["subject"]
    class_number = request.form["class_number"]
    semester = request.form["semester"]
    school_year = request.form["school_year"]
    professor = request.form["professor"]

    # class number should be an int
    try:
        class_number = int(class_number)
    except:
        return response({"msg": "Class Number must be an integer!"}, 400)

    # school year should be an int
    try:
        school_year = int(school_year)
    except:
        return response({"msg": "School Year must be an integer!"}, 400)

    if subject and class_number and semester and school_year and professor:
        cur = mysql.connection.cursor()
        # check for existing class
        cur.execute(
            "SELECT * FROM classes WHERE subject = %s AND class_number = %s AND semester = %s AND school_year = %s AND professor = %s",
            (subject, class_number, semester, school_year, professor),
        )
        data = cur.fetchone()
        if data:
            res = response({"msg": "A class with that information already exists"}, 409)
        else:
            cur.execute(
                "INSERT INTO classes (subject, class_number, semester, school_year, professor) VALUES (%s, %s, %s, %s, %s)",
                (subject, class_number, semester, school_year, professor),
            )
            mysql.connection.commit()
            cur.execute(
                "SELECT * FROM classes WHERE subject = %s AND class_number = %s",
                (subject, class_number),
            )
            new_class = cur.fetchone()
            res = response({"msg": "Class Created!", "class": new_class}, 201)
            cur.close()
    else:
        res = response({"msg": "Fields Empty!"}, 422)

    return res


@app.route("/class", methods=["GET"])
def get_all_classes():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM classes")
    data = cur.fetchall()
    cur.close()
    return response({"classes": data})


@app.route("/class/<int:id>", methods=["PUT"])
def update_class(id: int):
    try:
        request_data = request.get_json()
    except:
        return response({"msg: No Data Recieved!"}, 400)

    cur = mysql.connection.cursor()

    cur.execute("SELECT * FROM classes WHERE id = %s", (id,))
    class_ = cur.fetchone()

    if not class_:
        res = response({"msg": "Class Not Found!"}, 404)
    else:
        potential_args = [
            {"sql": "subject", "value": request_data.get("subject", None)},
            {"sql": "class_number", "value": request_data.get("class_number", None)},
            {"sql": "semester", "value": request_data.get("semester", None)},
            {"sql": "school_year", "value": request_data.get("school_year", None)},
            {"sql": "professor", "value": request_data.get("professor", None)},
        ]
        arg_count = 0
        sql_prompt = "UPDATE classes SET"

        for args in potential_args:
            if args["value"]:
                if arg_count > 0:
                    sql_prompt += ","
                arg_count += 1
                temp = args["value"]
                if type(args["value"]) is str:
                    temp = f'"{args["value"]}"'
                sql_prompt += f" {args['sql']} = {temp}"

        sql_prompt += f" WHERE id = {id}"

        if arg_count > 0:
            try:
                cur.execute(sql_prompt)
            except:
                cur.close()
                return response(
                    {"msg": "A class with that information already exists!"}, 400
                )

            cur.execute("SELECT * FROM classes WHERE id = %s", (id,))
            updated_class = cur.fetchone()

            res = response({"msg": "Class Updated!", "class": updated_class}, 200)
        else:
            res = response({"msg": "Fields Missing!"}, 400)

    mysql.connection.commit()
    cur.close()
    return res


@app.route("/class/<int:id>", methods=["DELETE"])
def delete_class(id: int):
    cur = mysql.connection.cursor()

    # check if class exists
    cur.execute("SELECT * FROM classes WHERE id = %s", (id,))
    class_ = cur.fetchone()
    if not class_:
        res = response({"msg": "Class Not Found!"}, 404)
    else:
        cur.execute("DELETE FROM classes WHERE id = %s", (id,))
        mysql.connection.commit()
        res = response({"msg": "Class Deleted!", "class": class_}, 200)
    cur.close()
    return res


###########################################
# ? Search / Enroll / Drop
###########################################
@app.route("/student/<string:email>/classes", methods=["GET"])
def get_student_classes(email: str):
    cur = mysql.connection.cursor()

    # check if student exists
    cur.execute("SELECT * FROM students WHERE email = %s", (email,))
    student = cur.fetchone()
    if not student:
        res = response({"msg": "Student Not Found!"}, 404)
    else:
        # get student enrollments
        cur.execute("SELECT * FROM enrollments WHERE student_id = %s", (student["id"],))
        enrollments = cur.fetchall()
        if not enrollments:
            res = response(
                {"msg": "Student Not Enrolled in Any Classes!", "classes": []}, 200
            )
        else:
            enrollment_ids = [enrollment["class_id"] for enrollment in enrollments]
            cur.execute("SELECT * FROM classes WHERE id IN %s", (enrollment_ids,))
            classes = cur.fetchall()
            res = response({"classes": classes}, 200)
    cur.close()
    return res


@app.route(
    "/student/<string:email>/class/subject/<string:subject>/class-number/<int:class_number>",
    methods=["POST"],
)
def class_enrollment(email: str, subject: str, class_number: str):
    cur = mysql.connection.cursor()

    # check if student exists
    cur.execute("SELECT * FROM students WHERE email = %s", (email,))
    student = cur.fetchone()
    if not student:
        res = response({"msg": "Student Not Found!"}, 404)
    else:
        # check if class exists
        cur.execute(
            "SELECT * FROM classes WHERE subject = %s AND class_number = %s",
            (subject, class_number),
        )
        class_ = cur.fetchone()
        if not class_:
            res = response({"msg": "Class Not Found!"}, 404)
        else:
            # check if student is already enrolled in class
            cur.execute(
                "SELECT * FROM enrollments WHERE student_id = %s AND class_id = %s",
                (student["id"], class_["id"]),
            )
            enrollment = cur.fetchone()
            if enrollment:
                res = response({"msg": "Student Already Enrolled in Class!"}, 400)
            else:
                cur.execute(
                    "INSERT INTO enrollments (student_id, class_id) VALUES (%s, %s)",
                    (student["id"], class_["id"]),
                )
                mysql.connection.commit()
                res = response({"msg": "Class Registered!"}, 201)

    cur.close()
    return res


@app.route(
    "/student/<string:email>/class/subject/<string:subject>/class-number/<int:class_number>",
    methods=["DELETE"],
)
def class_drop(email: str, subject: str, class_number: str):
    cur = mysql.connection.cursor()
    # check if student exists
    cur.execute("SELECT * FROM students WHERE email = %s", (email,))
    student = cur.fetchone()
    if not student:
        res = response({"msg": "Student Not Found!"}, 404)
    else:
        # check if class exists
        cur.execute(
            "SELECT * FROM classes WHERE subject = %s AND class_number = %s",
            (subject, class_number),
        )
        class_ = cur.fetchone()
        if not class_:
            res = response({"msg": "Class Not Found!"}, 404)
        else:
            # check if student is enrolled in class
            cur.execute(
                "SELECT * FROM enrollments WHERE student_id = %s AND class_id = %s",
                (student["id"], class_["id"]),
            )
            enrollment = cur.fetchone()
            if not enrollment:
                res = response({"msg": "Student Not Enrolled in Class!"}, 400)
            else:
                cur.execute(
                    "DELETE FROM enrollments WHERE student_id = %s AND class_id = %s",
                    (student["id"], class_["id"]),
                )
                mysql.connection.commit()
                res = response({"msg": "Class Dropped!"}, 200)

    cur.close()
    return res


@app.route("/student/search", methods=["GET"])
def student_search():
    sql_prompt = "SELECT DISTINCT s.id, s.email, s.full_name, s.grad_year FROM students s JOIN enrollments e ON s.id = e.student_id JOIN classes c ON e.class_id = c.id"
    potential_args = [
        {"key": "email", "sql": "s.email", "value": None},
        {"key": "full_name", "sql": "s.full_name", "value": None},
        {"key": "grad_year", "sql": "s.grad_year", "value": None},
        {"key": "subject", "sql": "c.subject", "value": None},
        {"key": "class_number", "sql": "c.class_number", "value": None},
        {"key": "semester", "sql": "c.semester", "value": None},
        {"key": "school_year", "sql": "c.school_year", "value": None},
        {"key": "professor", "sql": "c.professor", "value": None},
    ]
    collected_args = []
    for arg in potential_args:
        value = request.args.get(arg["key"])
        if value is not None:
            arg["value"] = value
            collected_args.append(arg)

    cur = mysql.connection.cursor()

    if len(collected_args) > 0:
        sql_prompt += " WHERE "
        for i, arg in enumerate(collected_args):
            if i > 0:
                sql_prompt += " AND "
            sql_prompt += f"{arg['sql']} like '%{arg['value']}%'"

        cur.execute(sql_prompt)
        result = cur.fetchall()
        result = [
            {
                k: v
                for k, v in row.items()
                if k in ["id", "email", "full_name", "grad_year"]
            }
            for row in result
        ]
        if result:
            res = response({"msg": "Query Successful!", "students": result})
        else:
            res = response({"msg": "No Results Found!", "students": []}, 404)
    else:
        res = response({"msg": "No Search Parameters Provided!"}, 400)

    cur.close()
    return res


@app.route("/class/search", methods=["GET"])
def class_search():
    sql_prompt = "SELECT * FROM classes"
    potential_args = [
        {"key": "subject", "sql": "subject", "value": None},
        {"key": "class_number", "sql": "class_number", "value": None},
        {"key": "semester", "sql": "semester", "value": None},
        {"key": "school_year", "sql": "school_year", "value": None},
        {"key": "professor", "sql": "professor", "value": None},
    ]
    collected_args = []
    for arg in potential_args:
        value = request.args.get(arg["key"])
        if value is not None:
            arg["value"] = value
            collected_args.append(arg)

    cur = mysql.connection.cursor()

    if len(collected_args) > 0:
        sql_prompt += " WHERE "
        for i, arg in enumerate(collected_args):
            if i > 0:
                sql_prompt += " AND "
            sql_prompt += f"{arg['sql']} like '%{arg['value']}%'"

        cur.execute(sql_prompt)
        result = cur.fetchall()
        if result:
            res = response({"msg": "Query Successful!", "classes": result})
        else:
            res = response({"msg": "No Results Found!", "classes": []}, 404)
    else:
        res = response({"msg": "No Search Parameters Provided!"}, 400)

    cur.close()
    return res


###########################################
# ? ERROR HANDLING
###########################################


@app.errorhandler(404)
def not_found(e):
    return response({"msg": "Not Found!"}, 404)


def main():
    if __name__ == "__main__":
        app.run(host="0.0.0.0", debug=True)


main()
