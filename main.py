from flask import Flask, request, make_response, redirect, url_for
from flask_pymongo import PyMongo, ObjectId

"""
Description: This project will act as a way to connect students (previous, current, or future) to track the classes they have taken.
Students sign up with their school email
Students can register for existing or new classes and say the semester they have taken the class.
Users may also search for other individuals who have taken / will take a given class; allowing them to network and collaborate with their peers.
"""

app = Flask(__name__)
app.config["MONGO_URI"] = (
    "mongodb://admin:password@127.0.0.1:27017/main?authSource=admin"
)
mongo = PyMongo(app)


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
    students = [
        {
            "email": "john@csu.fullerton.edu",
            "full_name": "John Smith",
            "grad_year": 2023,
        },
        {
            "email": "jane@csu.fullerton.edu",
            "full_name": "Jane Smith",
            "grad_year": 2022,
        },
        {
            "email": "jack@csu.fullerton.edu",
            "full_name": "Jack Smith",
            "grad_year": 2021,
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
    return redirect(url_for("get_all_classes"))


@app.route("/login", methods=["POST"])
def login():
    return redirect(url_for("index"))


###########################################
# ? STUDENT CRUD
###########################################
@app.route("/student", methods=["POST"])
def create_student():
    students = mongo.db.students

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
        if students.find_one({"email": email}):
            return response({"msg": "A student with that email already exists"}, 409)

        students.insert_one(
            {"email": email, "full_name": full_name, "grad_year": grad_year}
        )
        student = students.find_one({"email": email})
        student["_id"] = str(student["_id"])

    else:
        return response({"msg": "Fields Empty!"}, 400)
    return response({"msg": "Student Created!", "student": student}, 201)


@app.route("/student/<string:email>", methods=["GET"])
def get_student(email):
    student = mongo.db.students.find_one({"email": email})
    if not student:
        return response({"msg": "Student Not Found!"}, 404)

    student["_id"] = str(student["_id"])
    return response({"student": student})


@app.route("/student/class/<string:id>", methods=["GET"])
def get_students_by_enrollments_in_class(id: str):
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

    class_["_id"] = str(class_["_id"])

    return response({"class": class_, "students": students})


@app.route("/student/<string:email>", methods=["PUT"])
def update_student(email):
    try:
        request_data = request.get_json()
    except:
        return response({"msg": "No data provided!"}, 400)

    student = mongo.db.students.find_one({"email": email})
    if not student:
        return response({"msg": "Student Not Found!"}, 404)

    updated_data = {
        k: v for k, v in request_data.items() if k in ["full_name", "grad_year"]
    }

    if len(updated_data) == 0:
        return response({"msg": "Fields Missing!"}, 400)

    result = mongo.db.students.update_one({"email": email}, {"$set": updated_data})
    if result.modified_count == 0:
        return response({"msg": "No changes were made"}, 200)

    student = mongo.db.students.find_one({"email": email})
    student["_id"] = str(student["_id"])
    return response({"msg": "Student Updated!", "student": student})


@app.route("/student/<string:email>", methods=["DELETE"])
def delete_student(email):
    result = mongo.db.students.delete_one({"email": email})
    if result.deleted_count == 0:
        return response({"msg": "Student Not Found!"}, 404)
    return response({"msg": "Student Deleted!"}, 200)


##########################################
# ? CLASS CRUD
##########################################
@app.route("/class", methods=["POST"])
def create_class():
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
def get_all_classes():
    classes = list(mongo.db.classes.find({}))
    for class_ in classes:
        class_["_id"] = str(class_["_id"])
    return response({"classes": classes})


@app.route("/class/<string:id>", methods=["PUT"])
def update_class(id: str):
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
def delete_class(id: str):
    if not ObjectId.is_valid(id):
        return response({"msg": "Invalid ID!"}, 400)
    id = ObjectId(id)

    result = mongo.db.classes.delete_one({"_id": id})
    if result.deleted_count == 0:
        return response({"msg": "Class Not Found!"}, 404)
    return response({"msg": "Class Deleted!"}, 200)


###########################################
# ? Search / Enroll / Drop
###########################################
@app.route("/student/<string:email>/classes", methods=["GET"])
def get_student_classes(email: str):
    student = mongo.db.students.find_one({"email": email})
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
    "/student/<string:email>/class/<string:id>",
    methods=["POST"],
)
def class_enrollment(email: str, id: str):
    student = mongo.db.students.find_one({"email": email})
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
    "/student/<string:email>/class/<string:id>",
    methods=["DELETE"],
)
def class_drop(email: str, id: str):
    student = mongo.db.students.find_one({"email": email})
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
def student_search():
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
def class_search():
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
