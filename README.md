# cpsc-449-final

## About

This project will act as a way to connect students (previous, current, or future) to track the classes they have taken. Students sign up with their school email. Students can register for existing or new classes and say the semester they have taken the class. You can add new classes to the database. Users may also search for other individuals who have taken / will take a given class; allowing them to network and collaborate with their peers.

## Frontend Pages

- Home Page:
  - Login form for existing users.
  - Sign-up button leading to a registration form.
  - Includes a button to reseed the database with sample data. (Only available in development)
- Sign-up Page:
  - Registration form with fields for Email, Full Name, Graduation Year, and Password.
- Dashboard:
  - Displays all classes the logged-in student is enrolled in.
  - Provides links to detailed class views and options to drop classes.
- Account Page:
  - Shows user profile information (password excluded).
  - Options to update profile details and upload a profile image.
  - Button to delete the account.
- Search Pages:
  - Two forms for searching: one for students and another for classes.
  - Displays results with options to view detailed profiles or class details.
- Student Profile Page:
  - Displays student's basic information and list of enrolled classes.
  - Option to view the student's image if available.
- Class Detail Page:
  - Shows detailed information about the class including enrolled students.
  - Options to edit, delete, enroll in, or drop the class.
- All Classes Page:
  - Form to input new class details such as Subject, Class Number, Semester, School Year, and Professor.
  - Lists all available classes with options to view, edit, delete, or enroll directly from the list.
- Class Edit Page:
  - Form to edit class details.

## Dependencies

python==^3.11
flask==^3.0.2
flask-pymongo==^2.3.0
pyjwt==^2.8.0

## How to run

`python main.py`

This runs the development server on localhost:5000

This is not suitable for production use. For production use, use a production WSGI server like gunicorn or uWSGI.

Go to localhost:5000 in your browser to view the application.

You will be greeted with the home page. You can sign up for an account or log in with an existing account.

You can click in the bottom left corner of the home page to reseed the database with some sample data.

Create an account and log in to view the dashboard. From the dashboard, you can view your profile, search for classes or students, and enroll in classes.

## Developers

Nadeem Maida
Francisco Ocegueda
