# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Teacher sign-in required to sign up or unregister students

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Add teacher accounts to `src/teachers.json` in the format:

   ```
   {
     "teachers": [
       {
         "username": "teacher-name",
         "password_hash": "pbkdf2_sha256$600000$BASE64_SALT$BASE64_DIGEST"
       }
     ]
   ```

   Generate a password hash without putting the password in shell history:

   ```
   python - <<'PY'
   import base64
   import getpass
   import hashlib
   import secrets

   password = getpass.getpass("Teacher password: ")
   salt = secrets.token_bytes(16)
   digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000)
   print("pbkdf2_sha256$600000$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode())
   PY
   ```

   Store only the generated hash in the file; do not commit plaintext passwords.

3. Set a stable session signing secret and run the application:

   ```
   export SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
   uvicorn app:app --app-dir src --reload
   ```

   Set `SECURE_COOKIES=true` when serving the application over HTTPS.

4. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| GET    | `/auth/session`                                                    | Check whether the current browser session is signed in as a teacher |
| POST   | `/auth/login`                                                      | Sign in with a teacher username and password                        |
| POST   | `/auth/logout`                                                     | Sign out the current browser session                                |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Sign up a student (teacher session required)                         |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Unregister a student (teacher session required)                  |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

All data is stored in memory, which means data will be reset when the server restarts.
Teacher password hashes are read from `teachers.json` when the API starts.
