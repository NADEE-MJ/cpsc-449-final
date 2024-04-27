import jwt
import os
import datetime
from functools import wraps
from flask import (
    Flask,
    request,
    make_response,
    redirect,
    url_for,
    send_from_directory,
    render_template,
)
from flask_pymongo import PyMongo, ObjectId
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

"""
Description: This project will act as a way to connect students (previous, current, or future) to track the classes they have taken.
Students sign up with their school email
Students can register for existing or new classes and say the semester they have taken the class.
Users may also search for other individuals who have taken / will take a given class; allowing them to network and collaborate with their peers.
"""

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "my_precious_secret_key")
app.config["MONGO_URI"] = (
    "mongodb://admin:password@127.0.0.1:27017/main?authSource=admin"
)
app.config["UPLOAD_EXTENSIONS"] = [".jpg", ".png", ".gif"]
app.config["UPLOAD_PATH"] = "uploads"
mongo = PyMongo(app)

os.makedirs(app.config["UPLOAD_PATH"], exist_ok=True)


def response(data, status_code=200, headers=None):
    """
    Helper function to create a response with the correct headers

    Args:
        data (dict): The data to be returned in the response
        status_code (int): The status code of the response, defaults to 200

    Returns:
        Response: The response object
    """
    res = make_response(data, status_code)
    res.headers["Content-Type"] = "application/json"

    if headers:
        for key, value in headers.items():
            res.headers[key] = value
    return res


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get("token")
        if not token:
            return response({"msg": "Token is missing!"}, 401)
        try:
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            current_user = mongo.db.students.find_one(
                {"_id": ObjectId(data["user_id"])}
            )
        except:
            return response({"msg": "Token is invalid!"}, 401)

        if not current_user:
            return response({"msg": "User not found!"}, 404)

        kwargs["current_user"] = current_user

        return f(*args, **kwargs)

    return decorated


###########################################
# ? DATABASE
###########################################
@app.route("/initialize-db", methods=["POST"])
def initialize_db():
    # Dropping collections if they exist
    mongo.db.students.drop()
    mongo.db.classes.drop()
    mongo.db.enrollments.drop()

    # Optionally, you can create indexes here
    mongo.db.students.create_index("email", unique=True)
    mongo.db.classes.create_index(
        [
            ("subject", 1),
            ("class_number", 1),
            ("semester", 1),
            ("school_year", 1),
            ("professor", 1),
        ],
        unique=True,
    )

    return response({"msg": "Database Initialized!"})


@app.route("/seed-db", methods=["POST"])
def seed_db():
    initialize_db()
    password = generate_password_hash("password")
    students = [
        {
            "email": "john@csu.fullerton.edu",
            "full_name": "John Smith",
            "grad_year": 2023,
            "password": password,
        },
        {
            "email": "jane@csu.fullerton.edu",
            "full_name": "Jane Smith",
            "grad_year": 2022,
            "password": password,
        },
        {
            "email": "jack@csu.fullerton.edu",
            "full_name": "Jack Smith",
            "grad_year": 2021,
            "password": password,
        },
    ]
    # Inserting students and obtaining inserted_ids for further reference
    inserted_students = mongo.db.students.insert_many(students).inserted_ids

    classes = [
        {
            "subject": "CPSC",
            "class_number": 349,
            "semester": "Fall",
            "school_year": 2021,
            "professor": "Dr. Smith",
        },
        {
            "subject": "CPSC",
            "class_number": 335,
            "semester": "Fall",
            "school_year": 2021,
            "professor": "Dr. Smith",
        },
    ]
    # Inserting classes and obtaining inserted_ids for enrollments
    inserted_classes = mongo.db.classes.insert_many(classes).inserted_ids

    enrollments = [
        {"student_id": inserted_students[0], "class_id": inserted_classes[0]},
        {"student_id": inserted_students[1], "class_id": inserted_classes[0]},
        {"student_id": inserted_students[1], "class_id": inserted_classes[1]},
        {"student_id": inserted_students[2], "class_id": inserted_classes[1]},
    ]
    mongo.db.enrollments.insert_many(enrollments)

    return response({"msg": "Database Seeded!"})


###########################################
# ? LOGIN
###########################################
# ! NOT IMPLEMENTED
@app.route("/", methods=["GET"])
def index():
    return redirect(url_for("home"))


@app.route("/home", methods=["GET"])
def home():
    # Attempt to get the token from cookies
    token = request.cookies.get("token")
    if token:
        try:
            # Validate token and redirect to dashboard if valid
            jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            return redirect(url_for("dashboard"))
        except jwt.ExpiredSignatureError:
            pass  # Token is expired, fall through to show login
        except jwt.InvalidTokenError:
            pass  # Token is invalid, fall through to show login

    # If no valid token, render the login page
    return render_template("login.html")


@app.route("/signup", methods=["GET"])
def signup():
    return render_template("signup.html")


@app.route("/dashboard", methods=["GET"])
@token_required
def dashboard(current_user):
    classes = list(
        mongo.db.enrollments.find({"student_id": ObjectId(current_user["_id"])})
    )
    class_details = [
        mongo.db.classes.find_one({"_id": class_["class_id"]}) for class_ in classes
    ]
    return render_template(
        "dashboard.html", username=current_user["full_name"], classes=class_details
    )


@app.route("/student-search", methods=["GET"])
@token_required
def student_search_page(current_user):
    return render_template("student_search.html")


@app.route("/class-search", methods=["GET"])
@token_required
def class_search_page(current_user):
    return render_template("class_search.html")


@app.route("/account", methods=["GET"])
@token_required
def account(current_user):
    return render_template(
        "account.html",
        email=current_user["email"],
        full_name=current_user["full_name"],
        grad_year=current_user["grad_year"],
    )


@app.route("/login", methods=["POST"])
def login():
    request_data = request.get_json()
    if not request_data:
        return response(
            {"msg": "No data provided!"},
            400,
            headers={"WWW-Authenticate": 'Basic realm="Login required!"'},
        )

    email = request_data.get("email")
    password = request_data.get("password")
    if not email or not password:
        return response(
            {"msg": "Fields Missing!"},
            400,
            headers={"WWW-Authenticate": 'Basic realm="Login required!"'},
        )

    student = mongo.db.students.find_one({"email": email})
    if not student:
        return response(
            {"msg": "Student Not Found!"},
            404,
            headers={"WWW-Authenticate": 'Basic realm="Login required!"'},
        )

    if not check_password_hash(student["password"], password):
        return response(
            {"msg": "Invalid Credentials!"},
            401,
            headers={"WWW-Authenticate": 'Basic realm="Login required!"'},
        )

    token = jwt.encode(
        {
            "user_id": str(student["_id"]),
            "exp": datetime.datetime.now(tz=datetime.UTC)
            + datetime.timedelta(hours=24),
        },
        app.config["SECRET_KEY"],
    )
    res = response({"token": token}, 200)
    res.set_cookie("token", token, httponly=True)
    return res


###########################################
# ? STUDENT CRUD
###########################################
@app.route("/student", methods=["POST"])
def create_student():
    students = mongo.db.students

    fields = ["email", "full_name", "grad_year", "password"]
    for field in fields:
        if field not in request.form:
            return response({"msg": "Fields Missing!"}, 400)
    email = request.form["email"]
    full_name = request.form["full_name"]
    grad_year = request.form["grad_year"]
    password = request.form["password"]

    # grad year should be an int
    try:
        grad_year = int(grad_year)
    except:
        return response({"msg": "Grad Year must be an integer!"}, 400)

    if email and full_name and grad_year and password:
        if students.find_one({"email": email}):
            return response({"msg": "A student with that email already exists"}, 409)

        password = generate_password_hash(password)

        students.insert_one(
            {
                "email": email,
                "full_name": full_name,
                "grad_year": grad_year,
                "password": password,
            }
        )
        student = students.find_one({"email": email})
        student["_id"] = str(student["_id"])
        del student["password"]

    else:
        return response({"msg": "Fields Empty!"}, 400)
    return response({"msg": "Student Created!", "student": student}, 201)


@app.route("/student/<string:id>", methods=["GET"])
@token_required
def get_student(id: str, current_user: dict):
    if not ObjectId.is_valid(id):
        return response({"msg": "Invalid ID!"}, 400)
    id = ObjectId(id)
    student = mongo.db.students.find_one({"_id": id})
    if not student:
        return response({"msg": "Student Not Found!"}, 404)

    student["_id"] = str(student["_id"])
    del student["password"]

    return response({"student": student})


@app.route("/student/class/<string:id>", methods=["GET"])
@token_required
def get_students_by_enrollments_in_class(id: str, current_user: dict):
    if not ObjectId.is_valid(id):
        return response({"msg": "Invalid ID!"}, 400)
    id = ObjectId(id)
    class_ = mongo.db.classes.find_one({"_id": id})
    if not class_:
        return response({"msg": "Class Not Found!"}, 404)

    enrollments = list(mongo.db.enrollments.find({"class_id": id}))

    student_ids = [enrollment["student_id"] for enrollment in enrollments]

    students = list(mongo.db.students.find({"_id": {"$in": student_ids}}))

    for student in students:
        student["_id"] = str(student["_id"])
        del student["password"]

    class_["_id"] = str(class_["_id"])

    return response({"class": class_, "students": students})


@app.route("/student", methods=["PUT"])
@token_required
def update_student(current_user: dict):
    try:
        request_data = request.get_json()
    except:
        return response({"msg": "No data provided!"}, 400)

    student = mongo.db.students.find_one({"_id": current_user["_id"]})
    if not student:
        return response({"msg": "Student Not Found!"}, 404)

    updated_data = {
        k: v for k, v in request_data.items() if k in ["full_name", "grad_year"]
    }

    if len(updated_data) == 0:
        return response({"msg": "Fields Missing!"}, 400)

    result = mongo.db.students.update_one(
        {"_id": current_user["_id"]}, {"$set": updated_data}
    )
    if result.modified_count == 0:
        return response({"msg": "No changes were made"}, 200)

    student = mongo.db.students.find_one({"_id": current_user["_id"]})
    student["_id"] = str(student["_id"])
    del student["password"]

    return response({"msg": "Student Updated!", "student": student})


@app.route("/student", methods=["DELETE"])
@token_required
def delete_student(current_user: dict):
    result = mongo.db.students.delete_one({"email": current_user["email"]})
    if result.deleted_count == 0:
        return response({"msg": "Student Not Found!"}, 404)

    mongo.db.enrollments.delete_many({"student_id": current_user["_id"]})
    return response({"msg": "Student Deleted!"}, 200)


###########################################
# ? FILE HANDLING
###########################################
@app.route("/student/upload", methods=["POST"])
@token_required
def upload_student_image(current_user: dict):
    try:
        uploaded_files = request.files
    except:
        return response({"msg": "No file provided!"}, 400)

    if "file" not in uploaded_files:
        return response({"msg": "No file provided!"}, 400)

    if len(uploaded_files) > 1:
        return response({"msg": "Only one file can be uploaded!"}, 400)

    uploaded_file = request.files["file"]

    if not uploaded_file:
        return response({"msg": "No file provided!"}, 400)

    filename = secure_filename(uploaded_file.filename)
    if filename != "":
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in app.config["UPLOAD_EXTENSIONS"]:
            return response({"msg": "Invalid file extension!"}, 400)

        file_path = os.path.join(
            app.config["UPLOAD_PATH"], f"{str(current_user['_id'])}{file_ext}"
        )
        uploaded_file.save(file_path)

        mongo.db.students.update_one(
            {"_id": current_user["_id"]}, {"$set": {"image_path": file_path}}
        )

        return response({"msg": "File uploaded successfully!", "path": file_path})
    else:
        return response({"msg": "Invalid file name!"}, 400)


@app.route("/student/<string:id>/image", methods=["GET"])
@token_required
def get_student_image(id: str, current_user: dict):
    if not ObjectId.is_valid(id):
        return response({"msg": "Invalid ID!"}, 400)
    id = ObjectId(id)
    student = mongo.db.students.find_one({"_id": id})
    if not student:
        return response({"msg": "Student not found!"}, 404)

    if "image_path" in student and os.path.exists(student["image_path"]):
        return send_from_directory(
            os.path.dirname(student["image_path"]),
            os.path.basename(student["image_path"]),
        )
    else:
        return response({"msg": "No image found for this student."}, 404)


##########################################
# ? CLASS CRUD
##########################################
@app.route("/class", methods=["POST"])
@token_required
def create_class(current_user: dict):
    classes = mongo.db.classes

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

    if (
        not subject
        or not class_number
        or not semester
        or not school_year
        or not professor
    ):
        return response({"msg": "Fields Empty!"}, 422)

    data = {
        "subject": subject,
        "class_number": class_number,
        "semester": semester,
        "school_year": school_year,
        "professor": professor,
    }

    if classes.find_one(data):
        return response({"msg": "A class with that information already exists"}, 409)

    class_id = classes.insert_one(data).inserted_id
    class_ = classes.find_one({"_id": class_id})
    class_["_id"] = str(class_["_id"])
    return response({"msg": "Class Created!", "class": class_}, 201)


@app.route("/class", methods=["GET"])
@token_required
def get_all_classes(current_user: dict):
    classes = list(mongo.db.classes.find({}))
    for class_ in classes:
        class_["_id"] = str(class_["_id"])
    return response({"classes": classes})


@app.route("/class/<string:id>", methods=["PUT"])
@token_required
def update_class(id: str, current_user: dict):
    try:
        request_data = request.get_json()
    except:
        return response({"msg": "No Data Received!"}, 400)

    classes = mongo.db.classes
    if not ObjectId.is_valid(id):
        return response({"msg": "Invalid ID!"}, 400)

    id = ObjectId(id)
    class_ = classes.find_one({"_id": id})

    if not class_:
        return response({"msg": "Class Not Found!"}, 404)

    if "class_number" in request_data:
        try:
            request_data["class_number"] = int(request_data["class_number"])
        except:
            return response({"msg": "Class Number must be an integer!"}, 422)

    if "school_year" in request_data:
        try:
            request_data["school_year"] = int(request_data["school_year"])
        except:
            return response({"msg": "School Year must be an integer!"}, 422)

    updated_data = {
        k: v
        for k, v in request_data.items()
        if k in ["subject", "class_number", "semester", "school_year", "professor"]
    }

    if len(updated_data) == 0:
        return response({"msg": "Fields Missing!"}, 400)

    try:
        result = classes.update_one({"_id": id}, {"$set": updated_data})
    except:
        return response({"msg": "A class with that information already exists!"}, 400)

    if result.modified_count == 0:
        return response({"msg": "No changes were made"}, 200)

    class_ = classes.find_one({"_id": id})
    class_["_id"] = str(class_["_id"])
    return response({"msg": "Class Updated!", "class": class_})


@app.route("/class/<string:id>", methods=["DELETE"])
@token_required
def delete_class(id: str, current_user: dict):
    if not ObjectId.is_valid(id):
        return response({"msg": "Invalid ID!"}, 400)
    id = ObjectId(id)

    result = mongo.db.classes.delete_one({"_id": id})
    if result.deleted_count == 0:
        return response({"msg": "Class Not Found!"}, 404)

    mongo.db.enrollments.delete_many({"class_id": id})
    return response({"msg": "Class Deleted!"}, 200)


###########################################
# ? Search / Enroll / Drop
###########################################
@app.route("/student/<string:id>/classes", methods=["GET"])
@token_required
def get_student_classes(id: str, current_user: dict):
    if not ObjectId.is_valid(id):
        return response({"msg": "Invalid ID!"}, 400)
    id = ObjectId(id)
    student = mongo.db.students.find_one({"_id": id})
    if not student:
        return response({"msg": "Student Not Found!"}, 404)

    enrollments = list(mongo.db.enrollments.find({"student_id": student["_id"]}))
    if not enrollments:
        return response(
            {"msg": "Student Not Enrolled in Any Classes!", "classes": []}, 200
        )

    class_ids = [enrollment["class_id"] for enrollment in enrollments]
    classes = list(mongo.db.classes.find({"_id": {"$in": class_ids}}))

    for class_ in classes:
        class_["_id"] = str(class_["_id"])

    return response({"classes": classes}, 200)


@app.route(
    "/student/class/<string:id>",
    methods=["POST"],
)
@token_required
def class_enrollment(id: str, current_user: dict):
    student = mongo.db.students.find_one({"_id": current_user["_id"]})
    if not student:
        return response({"msg": "Student Not Found!"}, 404)

    if not ObjectId.is_valid(id):
        return response({"msg": "Invalid ID!"}, 400)
    id = ObjectId(id)

    class_ = mongo.db.classes.find_one({"_id": id})
    if not class_:
        return response({"msg": "Class Not Found!"})

    enrollment = mongo.db.enrollments.find_one(
        {"student_id": student["_id"], "class_id": class_["_id"]}
    )
    if enrollment:
        return response({"msg": "Student Already Enrolled in Class!"}, 400)

    mongo.db.enrollments.insert_one(
        {"student_id": student["_id"], "class_id": class_["_id"]}
    )
    return response({"msg": "Class Registered!"}, 201)


@app.route(
    "/student/class/<string:id>",
    methods=["DELETE"],
)
@token_required
def class_drop(id: str, current_user: dict):
    student = mongo.db.students.find_one({"_id": current_user["_id"]})
    if not student:
        return response({"msg": "Student Not Found!"}, 404)

    if not ObjectId.is_valid(id):
        return response({"msg": "Invalid ID!"}, 400)
    id = ObjectId(id)

    class_ = mongo.db.classes.find_one({"_id": id})
    if not class_:
        return response({"msg": "Class Not Found!"}, 404)

    enrollment = mongo.db.enrollments.find_one(
        {"student_id": student["_id"], "class_id": class_["_id"]}
    )

    if not enrollment:
        return response({"msg": "Student Not Enrolled in Class!"}, 400)

    mongo.db.enrollments.delete_one(
        {"student_id": student["_id"], "class_id": class_["_id"]}
    )
    return response({"msg": "Class Dropped!"}, 200)


@app.route("/student/search", methods=["GET"])
@token_required
def student_search(current_user: dict):
    search_params = {
        "email": request.args.get("email"),
        "full_name": request.args.get("full_name"),
        "grad_year": request.args.get("grad_year"),
        "classes.subject": request.args.get("subject"),
        "classes.class_number": request.args.get("class_number"),
        "classes.semester": request.args.get("semester"),
        "classes.school_year": request.args.get("school_year"),
        "classes.professor": request.args.get("professor"),
    }

    # Remove None values from search parameters
    query = {k: v for k, v in search_params.items() if v is not None}

    # Convert numeric values from strings to integers
    numeric_fields = ["grad_year", "classes.class_number", "classes.school_year"]
    for field in numeric_fields:
        if field in query:
            try:
                query[field] = int(query[field])
            except ValueError:
                return response(
                    {
                        "msg": f"{field.split('.')[-1].replace('_', ' ').title()} must be an integer!"
                    },
                    400,
                )

    # Adjust the aggregation pipeline
    pipeline = [
        {
            "$lookup": {
                "from": "enrollments",
                "localField": "_id",
                "foreignField": "student_id",
                "as": "enrollment_data",
            }
        },
        {"$unwind": {"path": "$enrollment_data", "preserveNullAndEmptyArrays": True}},
        {
            "$lookup": {
                "from": "classes",
                "localField": "enrollment_data.class_id",
                "foreignField": "_id",
                "as": "class_info",
            }
        },
        {"$unwind": {"path": "$class_info", "preserveNullAndEmptyArrays": True}},
        {"$match": query},
        {
            "$group": {
                "_id": "$_id",
                "email": {"$first": "$email"},
                "full_name": {"$first": "$full_name"},
                "grad_year": {"$first": "$grad_year"},
                "classes": {
                    "$push": {
                        "$cond": [
                            {"$eq": ["$class_info", None]},
                            "$$REMOVE",
                            "$class_info",
                        ]
                    }
                },
            }
        },
        {
            "$project": {
                "_id": 1,
                "email": 1,
                "full_name": 1,
                "grad_year": 1,
                "password": 0,
                "classes": 1,
            }
        },
    ]

    results = list(mongo.db.students.aggregate(pipeline))
    if not results:
        return response({"msg": "No Results Found!", "students": []}, 404)

    # Convert ObjectId to string for output
    for student in results:
        student["_id"] = str(student["_id"])
        student["classes"] = [{**c, "_id": str(c["_id"])} for c in student["classes"]]

    return response({"msg": "Query Successful!", "students": results})


@app.route("/class/search", methods=["GET"])
@token_required
def class_search(current_user: dict):
    search_params = {
        "subject": request.args.get("subject"),
        "class_number": request.args.get("class_number"),
        "semester": request.args.get("semester"),
        "school_year": request.args.get("school_year"),
        "professor": request.args.get("professor"),
    }

    # Remove None values from search parameters
    query = {k: v for k, v in search_params.items() if v is not None}

    # Convert numbers to integers where necessary
    if "class_number" in query:
        try:
            query["class_number"] = int(query["class_number"])
        except ValueError:
            return response({"msg": "Class Number must be an integer!"}, 400)
    if "school_year" in query:
        try:
            query["school_year"] = int(query["school_year"])
        except ValueError:
            return response({"msg": "School Year must be an integer!"}, 400)

    # Find classes that match the query
    classes = list(mongo.db.classes.find(query))

    # Convert ObjectId to string for output
    for class_ in classes:
        class_["_id"] = str(class_["_id"])

    if not classes:
        return response({"msg": "No Results Found!", "classes": []}, 404)

    return response({"msg": "Query Successful!", "classes": classes})


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
