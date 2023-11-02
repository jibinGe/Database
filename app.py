from flask import Flask, request
from datetime import datetime, timezone, timedelta
import psycopg2
from flask import Flask, request, jsonify
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity, set_access_cookies, unset_jwt_cookies
)
import hmac
from flask_cors import CORS
import os
from dotenv import load_dotenv
load_dotenv(".env")
from functools import wraps
from flask_mail import Mail, Message
from operator import itemgetter
import calendar
from pytz import timezone  # Import the pytz library
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger


connection = psycopg2.connect(os.getenv("DATABASE_URL"))

SIGNIN = ("SELECT * FROM USERS WHERE Email = %s AND Password = %s")
VIEW_USER = ("SELECT * from USERS WHERE Email = '{0}'")
VIEW_CLINIC = ("SELECT * from CLINIC WHERE ID = {0}")
VERIFY_PATIENT = ("SELECT PatientID FROM PATIENT WHERE PatientID = '{0}'")
INSERT_PATIENT = ("INSERT INTO PATIENT (PatientID, FullName, DateOfBirth, CycleID, CreatedBy, Mobile, CreatedDate) VALUES (%s, %s, %s, %s, %s, %s, %s);")
UPDATE_PATIENT = ("UPDATE PATIENT SET FullName = '{1}', DateOfBirth = '{2}', CycleID = {3}, Mobile = '{4}' WHERE PatientID = '{0}'")
VIEW_PATIENT = ("SELECT * FROM PATIENT WHERE CreatedBy = '{0}' AND DeletedAt IS NULL ORDER BY ID DESC")
VIEW_PATIENT_BY_ID = ("SELECT * FROM PATIENT WHERE ID = {0}")

GET_ID = ("SELECT ID FROM PATIENT ORDER BY ID DESC LIMIT 1")
DELETE_PATIENT = ("UPDATE PATIENT SET DeletedAt = '{1}' WHERE PatientID = '{0}'")
GET_PATIENT_ID = ("SELECT ID FROM PATIENT WHERE PatientID = '{0}'")
INSERT_EMBRYO = (
    "INSERT INTO EMBRYO (EmbryoNumber, EmbryoName, EmbryoAge, CycleID, ScanDate, CollectionDate, TransferDate, Pregnancy, LiveBirth, ClinicalNotes, EmbryoStatus, PatientID, EmbryoState, Percentage, EmbryoLink,filename,Slno) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s,%s);"
)
UPDATE_EMBRYO = (
    "UPDATE EMBRYO SET  EmbryoName = '{1}', EmbryoAge = '{2}', CycleID = {3}, ScanDate = '{4}', CollectionDate = '{5}', TransferDate = '{6}', Pregnancy = '{7}', LiveBirth = '{8}', ClinicalNotes = '{9}', EmbryoStatus = '{10}', EmbryoNumber= '{11}' WHERE id = {0}"
)
UPDATE_EMBRYO_C = (
    "UPDATE EMBRYO SET  EmbryoName = '{1}', EmbryoAge = '{2}', CycleID = {3}, ScanDate = '{4}',CollectionDate = '{5}', TransferDate = NULL, Pregnancy = '{6}', LiveBirth = '{7}', ClinicalNotes = '{8}', EmbryoStatus = '{9}', EmbryoNumber= '{10}' WHERE id = {0}"
)
UPDATE_EMBRYO_T = (
    "UPDATE EMBRYO SET  EmbryoName = '{1}', EmbryoAge = '{2}', CycleID = {3}, ScanDate = '{4}',TransferDate = '{5}', CollectionDate = NULL,Pregnancy = '{6}', LiveBirth = '{7}', ClinicalNotes = '{8}', EmbryoStatus = '{9}', EmbryoNumber= '{10}' WHERE id = {0}"
)
UPDATE_EMBRYO_B = (
    "UPDATE EMBRYO SET  EmbryoName = '{1}', EmbryoAge = '{2}', CycleID = {3}, ScanDate = '{4}',CollectionDate = NULL,TransferDate = NULL,Pregnancy = '{5}', LiveBirth = '{6}', ClinicalNotes = '{7}', EmbryoStatus = '{8}', EmbryoNumber= '{9}' WHERE id = {0}"
)
# UPDATE_EMBRYO = (
#     "UPDATE EMBRYO SET  EmbryoName = '{1}', EmbryoAge = '{2}', CycleID = {3}, ScanDate = '{4}', CollectionDate = '{5}', TransferDate = '{6}', Pregnancy = '{7}', LiveBirth = '{8}', ClinicalNotes = '{9}', EmbryoStatus = '{10}', EmbryoNumber= '{11}' WHERE id = {0}"
# )
VIEW_EMBRYO = ("SELECT * FROM EMBRYO WHERE PatientID = '{0}'")

INSERT_USER = (
    "INSERT INTO users (password, fullname, email, mobile, accesslevel, clinicid) "
    "VALUES (%s, %s, %s, %s, %s, %s);"
)

DELETE_USER = (
    "DELETE FROM users "
    "WHERE id = %s"
)

UPDATE_USER = (
    "UPDATE users "
    "SET password = %s, fullname = %s, email = %s, mobile = %s, accesslevel = %s, clinicid = %s "
    "WHERE id = %s"
)

app = Flask(__name__)
CORS(app)
app.config['JWT_SECRET_KEY'] = 'genesys-2023-qwerty'
# app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=24)
jwt = JWTManager(app)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'genesysailabs@gmail.com'
app.config['MAIL_PASSWORD'] = 'tlrldtobrwfyxvpc'

mail = Mail(app)

# @app.after_request
# def refresh_expiring_jwts(response):
#     try:
#         exp_timestamp = get_jwt()["exp"]
#         now = datetime.now(timezone.ist)
#         target_timestamp = datetime.timestamp(now + timedelta(minutes=30))
#         if target_timestamp > exp_timestamp:
#             access_token = create_access_token(identity=get_jwt_identity())
#             set_access_cookies(response, access_token)
#         return response
#     except (RuntimeError, KeyError):
#         # Case where there is not a valid JWT. Just return the original response
#         return response

@app.route("/", methods=["GET"])
def home():
    return "Genesys Server is up and running"

@app.route("/login", methods=["POST"])
def auth_signin():
    data = request.get_json()
    username = data["username"]
    password = data["password"]

    with connection:
        with connection.cursor() as cursor:
            cursor.execute(SIGNIN, (username, password))
            user = cursor.fetchone()
            user = list(user)
            # del user[1]
            if user is not None:
                cursor.execute(VIEW_CLINIC.format(user[6]))
                clinic = cursor.fetchone()
                clinic_id=clinic[0]
                str_clinic = str(clinic_id)
                current_date = datetime.now().strftime("%Y-%m-%d")
                current_time = datetime.now().strftime("%H:%M:%S")

                cursor.execute("SELECT COUNT(*) FROM ActivityLog WHERE EmployeeName = %s AND LoginDate = %s AND Action = 'Login';", (username, current_date))
                login_count = cursor.fetchone()[0]
                

                if login_count == 0:
                    activity_data = {
                        "employee_name": username, 
                        "login_date": current_date,
                        "login_time": current_time,
                        "action_date": current_date,
                        "action": "Login",
                        "clinic":str_clinic
                    }
                    cursor.execute("INSERT INTO ActivityLog (EmployeeName, LoginDate, LoginTime, ActionDate, Action, ClinicId) "
                                "VALUES (%s, %s, %s, %s, %s, %s);",
                                (activity_data["employee_name"], activity_data["login_date"],
                                    activity_data["login_time"], activity_data["action_date"], activity_data["action"], activity_data["clinic"]))
 
                # Create the access token and return the response
                access_token = create_access_token(identity=username)
                response = jsonify({'login': True, 'access_token': access_token, 'user': user, 'clinic': clinic})
                set_access_cookies(response, access_token)
                return response
            else:
                return jsonify({'login': False, "message": f"invalid user"}), 401



@app.route("/user/get", methods=["GET"])
@jwt_required()
def user_get():
    current_user = get_jwt_identity()
    if current_user is not None: 
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(VIEW_USER.format(current_user))
                user = cursor.fetchone()
                return {"success": True, "user": user}
        return {"success": False, "message": "something went wrong"}
    return jsonify({"success": False, "message": "No authorization header"}), 401

@app.route("/clinic/get", methods=["GET"])
@jwt_required()
def clinic_get():
    current_user = get_jwt_identity()
    if current_user is not None: 
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(VIEW_USER.format(current_user))
                user = cursor.fetchone()
                cursor.execute(VIEW_CLINIC.format(user[6]))
                clinic = cursor.fetchone()
                return {"success": True, "clinic": clinic}
        return {"success": False, "message": "something went wrong"}
    return jsonify({"success": False, "message": "No authorization header"}), 401

@app.route("/patient/create", methods=["POST"])
@jwt_required()
def patient_create():
    current_user = get_jwt_identity()
    if current_user is not None:
        data = request.get_json()
        patient_id = data["patient_id"]
        full_name = data["full_name"]
        dob = data["dob"]
        cycle_id = data["cycle_id"]
        created_by = current_user
        mobile = data["mobile"]
        created_date = datetime.now().strftime("%Y-%m-%d")
        with connection:
            
            with connection.cursor() as cursor:
                cursor.execute(VERIFY_PATIENT.format(patient_id))
                id = cursor.fetchone()
                if id is not None and len(id) > 0:
                    return {"success": False, "message": "Duplicate patient ID"}
                else:
                    # Insert patient data into the Patient table
                    cursor.execute("SELECT clinicid FROM users where email= %s;",(current_user,))
                    clinicid=cursor.fetchone()
                    cid=clinicid[0]
                    patient_id=str(str(cid)+'_'+patient_id)
                    cursor.execute(INSERT_PATIENT, (patient_id, full_name, dob, cycle_id, created_by, mobile, created_date))
                    # Log the activity directly in the ActivityLog table
                    activity_data = {
                        "employee_name": current_user,
                        "patient_id": patient_id,  
                        "patient_name": full_name,
                        "action_date": datetime.now().strftime("%Y-%m-%d"),
                        "action": "Created",
                        "clinicid":clinicid
                    }
                    cursor.execute("INSERT INTO ActivityLog (EmployeeName, PatientID, PatientName, ActionDate, Action, clinicid) VALUES (%s, %s, %s, %s, %s, %s);",
                                   (activity_data["employee_name"],
                                    activity_data["patient_id"], activity_data["patient_name"],
                                    activity_data["action_date"], activity_data["action"], activity_data["clinicid"]))

                    cursor.execute(GET_ID)
                    id = cursor.fetchone()
                    return {"success": True, "message": "Patient details added", "id": id}
        return {"success": False, "message": "something went wrong"}
    return jsonify({"success": False, "message": "No authorization header"}), 401


# @app.route("/patient/create", methods=["POST"])
# @jwt_required()
# def patient_create():
#     current_user = get_jwt_identity()
    
#     if current_user is not None:
#         data = request.get_json()
        
#         try:
#             cursor = connection.cursor()
            
#             cursor.execute("SELECT clinicid FROM users WHERE email = %s;", (current_user,))
#             clinicid = cursor.fetchone()
            
#             if clinicid is not None:
#                 clinicid = clinicid[0]
#                 patient_id = data["patient_id"]
#                 full_name = data["full_name"]
#                 dob = data["dob"]
#                 cycle_id = data["cycle_id"]
#                 created_by = current_user
#                 mobile = data["mobile"]
#                 created_date = datetime.now().strftime("%Y-%m-%d")
                
#                 cursor.execute(VERIFY_PATIENT, (patient_id,))
#                 id = cursor.fetchone()
                
#                 if id is not None and len(id) > 0:
#                     return {"success": False, "message": "Duplicate patient ID"}
#                 else:
#                     cursor.execute(INSERT_PATIENT, (patient_id, full_name, dob, cycle_id, created_by, mobile, created_date))
                    
#                     # Log the activity directly in the ActivityLog table
#                     activity_data = {
#                         "employee_name": current_user,
#                         "patient_id": patient_id,
#                         "patient_name": full_name,
#                         "action_date": datetime.now().strftime("%Y-%m-%d"),
#                         "action": "Created",
#                         "clinicid": clinicid
#                     }
#                     cursor.execute("INSERT INTO ActivityLog (EmployeeName, PatientID, PatientName, ActionDate, Action, ClinicId) VALUES (%s, %s, %s, %s, %s, %s);",
#                                    (activity_data["employee_name"],
#                                     activity_data["patient_id"], activity_data["patient_name"],
#                                     activity_data["action_date"], activity_data["action"], activity_data["clinicid"]))
                    
#                     cursor.execute(GET_ID)
#                     id = cursor.fetchone()
#                     connection.commit()
#                     return {"success": True, "message": "Patient details added", "id": id}
#         except psycopg2.Error as e:
#             print("Database error:", e)
#             return {"success": False, "message": "Database error"}
#         finally:
#             cursor.close()
#             connection.close()

#     return jsonify({"success": False, "message": "No authorization header"}), 401

@app.route("/patient/update", methods=["POST"])
@jwt_required()
def patient_update():
    current_user = get_jwt_identity()
    if current_user is not None: 
        data = request.get_json()
        patient_id = data["patient_id"]
        full_name = data["full_name"]
        dob = data["dob"]
        cycle_id = data["cycle_id"]
        created_by = current_user
        mobile = data["mobile"]
        
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(UPDATE_PATIENT.format(patient_id, full_name, dob, cycle_id, mobile))
                return {"success": True, "message": "Patient details updated"}
        return {"success": False, "message": "something went wrong"}
    return jsonify({"success": False, "message": "No authorization header"}), 401

@app.route("/patient/delete", methods=["POST"])
@jwt_required()
def patient_delete():
    current_user = get_jwt_identity()
    if current_user is not None: 
        data = request.get_json()
        patient_id = data["patient_id"]
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(DELETE_PATIENT.format(patient_id, datetime.now()))
                return {"success": True, "message": "Patient details deleted"}
        return {"success": False, "message": "something went wrong"}
    return jsonify({"success": False, "message": "No authorization header"}), 401

# @app.route("/patient/get", methods=["GET"])
# @jwt_required()
# def patient_get():
#     current_user = get_jwt_identity()
#     if current_user is not None: 
#         with connection:
#             with connection.cursor() as cursor:
#                 cursor.execute(VIEW_PATIENT.format(current_user))
#                 patients = cursor.fetchall()
#                 return {"success": True, "patients": patients}
#         return {"success": False, "message": "something went wrong"}
#     return jsonify({"success": False, "message": "No authorization header"}), 401

# @app.route("/patient/get", methods=["GET"])
# @jwt_required()
# def patient_get():
#     current_user = get_jwt_identity()
    
#     if current_user is not None: 
#         with connection:
#             with connection.cursor() as cursor:
#                 cursor.execute(VIEW_PATIENT.format(current_user))
#                 patients = cursor.fetchall()
#                 # Modify the patient IDs to remove the clinic ID prefix
#                 modified_patients = []
#                 for patient in patients:
#                     patient_id = patient[1].split('_')[1]
#                     modified_patient = list(patient)
#                     modified_patient[1] = patient_id
#                     modified_patients.append(modified_patient)
                
#                 return {"success": True, "patients": modified_patients}
#         return {"success": False, "message": "Something went wrong"}
#     return jsonify({"success": False, "message": "No authorization header"}), 401

@app.route("/patient/get", methods=["GET"])
@jwt_required()
def patient_get():
    current_user = get_jwt_identity()
    if current_user is not None: 
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(VIEW_PATIENT.format(current_user))
                patients = cursor.fetchall()
                return {"success": True, "patients": patients}
        return {"success": False, "message": "something went wrong"}
    return jsonify({"success": False, "message": "No authorization header"}), 401
 
@app.route("/patient/get/<id>", methods=["GET"])
@jwt_required()
def patient_get_by_id(id):
    current_user = get_jwt_identity()
    cursor.execute("SELECT clinicid FROM users where email= %s;",(current_user,))
    clinicid=cursor.fetchone()
    cid=clinicid[0]
    patient_id=str(str(cid)+'_'+id)
    if current_user is not None:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(VIEW_PATIENT_BY_ID.format(id))
                patient = cursor.fetchall()

                # cursor.execute("SELECT FullName FROM PATIENT WHERE ID = %s;", (id,))
                # full_name = cursor.fetchone()
                # cursor.execute("SELECT PatientID FROM PATIENT WHERE ID = %s;", (id,))
                # patientid = cursor.fetchone()[0]  # Access the value using index 0
                # activity_data = {
                #     "employee_name": current_user,
                #     "patient_id": patientid,
                #     "patient_name": full_name[0],  # Access the value using index 0
                #     "action_date": datetime.now().strftime("%Y-%m-%d"),
                #     "action": "Viewed"
                # }
                # cursor.execute("INSERT INTO ActivityLog (EmployeeName, PatientID, PatientName, ActionDate, Action) "
                #                "VALUES (%s, %s, %s, %s, %s);",
                #                (activity_data["employee_name"], activity_data["patient_id"],
                #                 activity_data["patient_name"], activity_data["action_date"], activity_data["action"]))

                return {"success": True, "patient": patient, "cid": cid}

        return {"success": False, "message": "something went wrong"}
    return jsonify({"success": False, "message": "No authorization header"}), 401

def validate_json_data(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            data = request.get_json()
            if data is None or "embryo_details" not in data:
                raise ValueError("Invalid JSON data format")
            return fn(data, *args, **kwargs)
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 400
    return wrapper

@app.route("/embryo/create", methods=["POST"])
@jwt_required()
def embryo_create():
    current_user = get_jwt_identity()
    if current_user is not None: 
        data = request.get_json()
        embryo_number = data["embryo_number"]
        embryo_name = data["embryo_name"]
        embryo_age = data["embryo_age"]
        cycle_id = data["cycle_id"]
        scan_date = data["scan_date"]
        collection_date = data["collection_date"]
        transfer_date = data["transfer_date"]
        pregnancy = data["pregnancy"]
        live_birth = data["live_birth"]
        clinical_notes = data["clinical_notes"]
        embryo_status = data["embryo_status"]
        patient_id = data["patient_id"]
        percentage = data["percentage"]
        embryo_state = data["embryo_state"]
        embryo_link = data["embryo_link"]
        filename = data["filename"]
        slno = data["slno"]

        with connection:
            with connection.cursor() as cursor:
                cursor.execute(GET_PATIENT_ID.format(patient_id))
                patient_id_value = cursor.fetchone()
                cursor.execute(INSERT_EMBRYO, (embryo_number, embryo_name, embryo_age, cycle_id, scan_date, collection_date, transfer_date, pregnancy, live_birth, clinical_notes, embryo_status, patient_id, embryo_state, percentage, embryo_link,filename,slno))
                return {"success": True, "message": "Embryo details added"}
        return {"success": False, "message": "something went wrong"}
    return jsonify({"success": False, "message": "No authorization header"}), 401

@app.route("/embryo/create_embryo", methods=["POST"])
@jwt_required()
@validate_json_data
def embryo_create_delete(data):
    current_user = get_jwt_identity()
    if current_user is not None:
        embryo_details = data["embryo_details"]
        if not isinstance(embryo_details, list):
            return jsonify({"success": False, "message": "Invalid format for 'embryo_details'"}), 400
        with connection:
            with connection.cursor() as cursor:
                patient_id = embryo_details[0]["patient_id"]  # Assuming patient_id is common for all embryo details
                print(patient_id)
                cursor.execute("SELECT noofclick FROM patient WHERE id = %s", (patient_id,))
                current_click_count = cursor.fetchone()
                if current_click_count is not None and current_click_count[0] is not None:
                    current_click_count = current_click_count[0]
                else:
                    current_click_count = 0
                cursor.execute("UPDATE patient SET noofclick = %s, vewreportdate = %s WHERE id = %s", (current_click_count + 1, datetime.now().strftime("%Y-%m-%d"), patient_id))
                print(patient_id,current_click_count + 1)

                # Clear the existing embryo details for the patient_id
                cursor.execute("DELETE FROM embryo WHERE patientid = %s", (patient_id,))
                for embryo_data in embryo_details:
                    embryo_number = embryo_data["embryo_number"]
                    embryo_name = embryo_data["embryo_name"]
                    embryo_age = embryo_data["embryo_age"]
                    cycle_id = embryo_data["cycle_id"]
                    scan_date = embryo_data["scan_date"]
                    collection_date = embryo_data["collection_date"]
                    transfer_date = embryo_data["transfer_date"]
                    pregnancy = embryo_data["pregnancy"]
                    live_birth = embryo_data["live_birth"]
                    clinical_notes = embryo_data["clinical_notes"]
                    embryo_status = embryo_data["embryo_status"]
                    patient_id = embryo_data["patient_id"]
                    embryo_state = embryo_data["embryo_state"]
                    percentage = embryo_data["percentage"]
                    embryo_link = embryo_data["embryo_link"]
                    filename = embryo_data["filename"]
                    slno = embryo_data["slno"]

                    
                    try:
                        cursor.execute(INSERT_EMBRYO, (embryo_number, embryo_name, embryo_age, cycle_id, scan_date, collection_date, transfer_date, pregnancy, live_birth, clinical_notes, embryo_status, patient_id, embryo_state, percentage, embryo_link, filename, slno))
                        connection.commit()  # Commit the transaction if needed
                    except Exception as e:
                        connection.rollback()  # Rollback the transaction if an error occurs
                        return jsonify({"success": False, "message": str(e), "str(patient_id)": str(embryo_details)}), 500
                # Fetch the newly inserted embryo details for the patient_id
                cursor.execute("SELECT * FROM embryo WHERE patientid = %s", (patient_id,))
                inserted_embryo_details = cursor.fetchall()

        formatted_inserted_embryo_details = []
        for row in inserted_embryo_details:
            embryo_detail = {
                "id": row[0],
                "embryo_number": row[1],
                "embryo_name": row[2],
                "cycle_id": row[3],
                "scan_date": row[4],
                "collection_date": row[5],
                "transfer_date": row[6],
                "pregnancy": row[7],
                "live_birth": row[8],
                "clinical_notes": row[9],
                "embryo_status": row[10],
                "patient_id": row[11],
                "embryo_state": row[12],
                "percentage": row[13],
                "embryo_link": row[14],
                "filename": row[15],
                "embryo_age": row[16]
            }
            formatted_inserted_embryo_details.append(embryo_detail)

        response_data = {
            "success": True,
            "message": "Embryo details added",
            "embryo_details": formatted_inserted_embryo_details,
        }
        return jsonify(response_data), 200

    return jsonify({"success": False, "message": "No authorization header"}), 401



@app.route("/embryo/update", methods=["POST"])
@jwt_required()
def embryo_update():
    current_user = get_jwt_identity()
    if current_user is not None: 
        data = request.get_json()
        id = data["id"]
        embryo_name = data["embryo_name"]
        embryo_age = data["embryo_age"]
        cycle_id = data["cycle_id"]
        scan_date = data["scan_date"]
        collection_date = data["collection_date"]
        transfer_date = data["transfer_date"]
        pregnancy = data["pregnancy"]
        live_birth = data["live_birth"]
        clinical_notes = data["clinical_notes"]
        embryo_status = data["embryo_status"]
        embryo_number = data["embryo_number"]
        if collection_date is None and transfer_date is None:
            query=UPDATE_EMBRYO_B.format(id, embryo_name, embryo_age, cycle_id, scan_date,pregnancy, live_birth, clinical_notes, embryo_status, embryo_number)
            print("both is none")
        elif collection_date is None:
            query=UPDATE_EMBRYO_T.format(id, embryo_name, embryo_age, cycle_id, scan_date, transfer_date,pregnancy, live_birth, clinical_notes, embryo_status, embryo_number)
            print("collection_date is none")
        elif transfer_date is None:
            query=UPDATE_EMBRYO_C.format(id, embryo_name, embryo_age, cycle_id, scan_date, collection_date,pregnancy, live_birth, clinical_notes, embryo_status, embryo_number)
            print("transfer_date is none")
        else:
            query=UPDATE_EMBRYO.format(id, embryo_name, embryo_age, cycle_id, scan_date,collection_date,transfer_date, pregnancy, live_birth, clinical_notes, embryo_status, embryo_number)
            print("collection_date and transfer_date is not none")
        print(collection_date)
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                connection.commit()
                return {"success": True, "message": "Embryo details updated"}
        return {"success": False, "message": "something went wrong"}
    return jsonify({"success": False, "message": "No authorization header"}), 401

@app.route("/embryo/get/<patient_id>", methods=["GET"])
@jwt_required()
def embryo_get(patient_id):
    current_user = get_jwt_identity()
    if current_user is not None: 
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(GET_PATIENT_ID.format(patient_id))
                patient_id_value = cursor.fetchone()
                cursor.execute(VIEW_EMBRYO.format(patient_id_value[0]))
                embryo_details = cursor.fetchall()

                cursor.execute("SELECT FullName FROM PATIENT WHERE PatientID = %s;", (patient_id,))
                full_name = cursor.fetchone()
                # cursor.execute("SELECT PatientID FROM PATIENT WHERE ID = %s;", (id,))
                # patientid = cursor.fetchone()[0]  
                activity_data = {
                    "employee_name": current_user,
                    "patient_id": patient_id,
                    "patient_name": full_name[0],
                    "action_date": datetime.now().strftime("%Y-%m-%d"),
                    "action": "Viewed"
                }
                cursor.execute("INSERT INTO ActivityLog (EmployeeName, PatientID, PatientName, ActionDate, Action) "
                               "VALUES (%s, %s, %s, %s, %s);",
                               (activity_data["employee_name"], activity_data["patient_id"],
                                activity_data["patient_name"], activity_data["action_date"], activity_data["action"]))

                # Convert embryo data into desired output format
                formatted_embryo_details = []
                for row in embryo_details:
                    embryo_detail = {
                        "id": row[0],
                        "embryo_number": row[1],
                        "embryo_name": row[2],
                        "cycle_id": row[3],
                        "scan_date": row[4],
                        "collection_date": row[5],
                        "transfer_date": row[6],
                        "pregnancy": row[7],
                        "live_birth": row[8],
                        "clinical_notes": row[9],
                        "embryo_status":  row[10],
                        "patient_id": row[11],
                        "embryo_state": row[12],
                        "percentage": row[13],
                        "embryo_link": row[14],
                        "filename":row[15],
                        "embryo_age": row[16]
                    }
                    formatted_embryo_details.append(embryo_detail)

                return {"success": True, "embryo_details": formatted_embryo_details}
        return {"success": False, "message": "something went wrong"}
    return jsonify({"success": False, "message": "No authorization header"}), 401

@app.route("/user/create", methods=["POST"])
@jwt_required()
def user_create():
    current_user = get_jwt_identity()
    if current_user is not None: 
        data = request.get_json()
        password = data["password"]
        fullname = data["fullname"]
        email = data["email"]
        mobile = data["mobile"]
        accesslevel = data["accesslevel"]
        clinicid = data["clinicid"]
        
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(INSERT_USER, (password, fullname, email, mobile, accesslevel, clinicid))
                return {"success": True, "message": "User details added"}
        return {"success": False, "message": "something went wrong"}
    return jsonify({"success": False, "message": "No authorization header"}), 401

@app.route("/user/delete", methods=["POST"])
@jwt_required()
def user_delete():
    current_user = get_jwt_identity()
    if current_user is not None: 
        data = request.get_json()
        user_id = data["user_id"]
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(DELETE_USER, (user_id,))
                return {"success": True, "message": "User details deleted"}
        return {"success": False, "message": "something went wrong"}
    return jsonify({"success": False, "message": "No authorization header"}), 401

@app.route("/user/update", methods=["POST"])
@jwt_required()
def user_update():
    current_user = get_jwt_identity()
    if current_user is not None: 
        data = request.get_json()
        user_id = data["user_id"]
        password = data["password"]
        fullname = data["fullname"]
        email = data["email"]
        mobile = data["mobile"]
        accesslevel = data["accesslevel"]
        clinicid = data["clinicid"]

        with connection:
            with connection.cursor() as cursor:
                cursor.execute(UPDATE_USER, (password, fullname, email, mobile, accesslevel, clinicid, user_id))
                return {"success": True, "message": "User details updated"}
        return {"success": False, "message": "something went wrong"}
    return jsonify({"success": False, "message": "No authorization header"}), 401


@app.route("/employee/get", methods=["GET"])
@jwt_required()
def employee_get():
    current_user = get_jwt_identity()
    if current_user is not None:
        with connection:
            with connection.cursor() as cursor:
                query = "SELECT id, password, fullname, email, mobile, accesslevel, clinicid FROM users WHERE clinicid IN (SELECT clinicid FROM users WHERE email = '{id}')"
                query = query.format(id=current_user)
                cursor.execute(query)
                users = cursor.fetchall()

                # Convert the result from a list of tuples to a list of dictionaries
                users_data = []
                for user in users:
                    user_data = {
                        "id": user[0],
                        # "password": user[1],
                        "fullname": user[2],
                        "email": user[3],
                        "mobile": user[4],
                        "accesslevel": user[5],
                        "clinicid": user[6]
                    }
                    users_data.append(user_data)

                return jsonify({"success": True, "users": users_data})

        return jsonify({"success": False, "message": "Something went wrong"})
    return jsonify({"success": False, "message": "No authorization header"}), 401


@app.route("/activitylog/details", methods=["GET"])
@jwt_required()
def activitylog_details():
    current_user = get_jwt_identity()
    if current_user is not None:
        with connection:
            with connection.cursor() as cursor:
                # Retrieve the details from the activitylog table for the current user
                cursor.execute("SELECT clinicid FROM users where email= %s;",(current_user,))
                clinicid=cursor.fetchone()
                clinicid=clinicid[0]
                str_clinicid = str(clinicid)
                cursor.execute("SELECT EmployeeName, LoginDate, LoginTime FROM ActivityLog WHERE ClinicId=%s;",(str_clinicid,))
                activity_details = cursor.fetchall()
                

                # Convert the time object to a string before returning the response
                formatted_activity_details = []
                for activity in activity_details:
                    employee_name, login_date, login_time = activity
                    login_date_str = login_date.strftime("%Y-%m-%d") if login_date else None
                    login_time_str = login_time.strftime("%H:%M:%S") if login_time else None
                    cursor.execute("SELECT COUNT(*) FROM ActivityLog WHERE EmployeeName = %s AND ClinicId=%s AND Action = 'Created';", (employee_name,str_clinicid,))
                    created_count = cursor.fetchone()[0]
                    cursor.execute("SELECT FullName FROM Users WHERE email = %s", (employee_name,))
                    empname = cursor.fetchone()[0]
                    formatted_activity_details.append({
                        "EmployeeName": empname,
                        "EmployeeEmail": employee_name,
                        "LoginDate": login_date_str,
                        "LoginTime": login_time_str,
                        'created_count': created_count
                    })

                # Filter out entries where both LoginDate and LoginTime are null
                filtered_activity_details = [activity for activity in formatted_activity_details if activity["LoginDate"] is not None and activity["LoginTime"] is not None]

                return {"success": True, "activity_details": filtered_activity_details}

        return {"success": False, "message": "something went wrong"}
    return jsonify({"success": False, "message": "No authorization header"}), 401

@app.route("/activitylog/filter", methods=["GET"])
@jwt_required()
def activitylog_filter():
    current_user = get_jwt_identity()
    if current_user is not None:
        # Get the query parameters from the request
        employee_name = request.args.get('employee_name')
        action_date = request.args.get('action_date')

        with connection:
            with connection.cursor() as cursor:
                # Retrieve the details from the activitylog table based on the provided parameters
                cursor.execute("SELECT PatientID, PatientName, Action FROM activitylog WHERE EmployeeName=%s AND ActionDate=%s AND NOT Action='Login';", (employee_name, action_date))
                activity_details = cursor.fetchall()

                # Create a list of dictionaries for the formatted output
                formatted_activity_details = []
                for activity in activity_details:
                    patient_id, patient_name, action = activity
                    formatted_activity_details.append({
                        "PatientId": patient_id,
                        "PatientName": patient_name,
                        "Action": action,
                    })

                return {"success": True, "activity_details": formatted_activity_details}

        return {"success": False, "message": "something went wrong"}
    return jsonify({"success": False, "message": "No authorization header"}), 401

@app.route('/report_a_problem', methods=['POST'])
@jwt_required()
def send_email():
    try:
        data = request.json
        if not data:
            return jsonify({'message': 'No data received'}), 400

        problem_title = data.get('problem_title')
        sender_email = 'genesysailabs@gmail.com'
        description = data.get('description')
        status = 'Open'
        msg = Message(subject=problem_title,
                      sender=sender_email,
                      recipients=['jibingtsr@gmail.com','info@genesysailabs.com'],
                      body=description)
        mail.send(msg)

        if not problem_title or not description or not status:
            return jsonify({"error": "Missing required fields"}), 400

        cursor = connection.cursor()
        current_date = datetime.now().strftime("%Y-%m-%d")
        query = "INSERT INTO problem (problem_title, description, status, issue_date, resolve_date) VALUES (%s, %s, %s, %s, %s);"
        cursor.execute(query, (problem_title, description, status, current_date, None))
        connection.commit()

        return jsonify({'message': 'Email sent successfully and ticket raised'}), 200

    except Exception as e:
        return jsonify({'message': str(e)}), 500

@app.route("/clinic/topay", methods=["POST"])
@jwt_required()
def clinic_to_pay():
    try:
        data = request.get_json()
        current_clinic_id = data["clinic_id"]
        current_month = datetime.now().strftime("%Y-%m-%d")
        with connection.cursor() as cursor:
            cursor.execute("SELECT email FROM users WHERE clinicid = %s", (current_clinic_id,))
            clinic_users = cursor.fetchall()
        for user_id in clinic_users:
            with connection.cursor() as cursor:
                cursor.execute("SELECT p.noofclick, c.noofcycle, c.monthlyfee, c.extrafeeperpatients FROM patient p INNER JOIN clinic c ON p.createdby = %s AND c.id = %s", (user_id,current_clinic_id))
                patient_data = cursor.fetchall()
        print(patient_data)
        payment_summary = {
            "Payment Month": current_month,
        }
        
        return jsonify(payment_summary)
    
    except Exception as e:
        return jsonify({"success": False, "message": "An error occurred ", "error": str(e)}), 500



@app.route("/clinic/payment-summary", methods=["POST"])
@jwt_required()     
def clinic_payment_summary():   
    try:
        data = request.get_json()
        current_clinic_id = data["clinic_id"]
        current_user = get_jwt_identity()
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM accounts WHERE clinicid = %s", (current_clinic_id,))
            accounts = cursor.fetchall()
            print(accounts)
            payment_summary = []
            patient_data = get_accounts_data(current_user)
            payment_summary.extend(patient_data)
            for account in accounts:
                if len(account) >= 8:  # Check if the list has at least 8 elements
                    year_and_month = str(account[0])
                    year, month = year_and_month.split("-")
                    start_date = account[7]
                    next_due_date = start_date + timedelta(days=30)
                    due_in_timedelta = next_due_date - datetime.now().date()
                    due_in = str(due_in_timedelta.days) + ' Days'
                    payment_date = datetime.strptime(year_and_month, "%Y-%m")
                    formatted_payment_month = payment_date.strftime("%B %Y")
                    month_name = calendar.month_name[int(month)]
                    data = {
                        "payment_month": formatted_payment_month,
                        "patient_scanned": account[1],
                        "amount": account[2],
                        "next_bill_due_date": account[3],
                        "status": account[5],
                        "due_in": due_in,
                        "month": month_name,
                        "year": year,
                        "payment_date": payment_date
                    }
                    payment_summary.append(data)
                    payment_summary = sorted(payment_summary, key=itemgetter("payment_date"), reverse=True)
                    print(payment_summary)
                else:
                    app.logger.error("Account data is incomplete: %s", account)
            print(payment_summary)        
            return jsonify({"success": True, "payment_summary": payment_summary})

    except Exception as e:
        app.logger.error("An error occurred: %s", str(e))
        return jsonify({"success": False, "message": "An error occurred", "error": str(e)}), 500



@app.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    response = jsonify({'logout': True})
    unset_jwt_cookies(response)
    return response

def get_accounts_data(current_user):
    try:
        # patient data
        with connection.cursor() as cursor:
            cursor.execute("SELECT clinicid FROM users WHERE email = %s", (current_user,))
            clinicid = cursor.fetchall()
            clinicid=clinicid[0][0]
            cursor.execute("SELECT email FROM users WHERE clinicid = %s", (clinicid,))
            emails = cursor.fetchall()
            email_list = [email[0] for email in emails]
        for email in email_list:
            with connection.cursor() as cursor:
                cursor.execute("SELECT vewreportdate,noofclick FROM patient WHERE createdby = %s", (email,))
                patient_data_tuple=cursor.fetchall()
            patient_data = []
            for row in patient_data_tuple:
                vewreportdate = row[0]
                noofclick = row[1]
                if vewreportdate is not None:
                    vewreportdate = vewreportdate.strftime("%Y-%m-%d")
                else:
                    continue
                patient_data.append({"vewreportdate": vewreportdate, "noofclick": noofclick})
        #clinic data
        with connection.cursor() as cursor:
            cursor.execute("SELECT monthlyfee,extrafeeperpatients,noofcycle FROM clinic WHERE id = %s", (clinicid,))
            clinic_data_tuple = cursor.fetchall()
            clinic_data=[]
            for row in clinic_data_tuple:
                monthlyfee = row[0]
                extrafeeperpatients = row[1]
                noofcycle =row[2]
                clinic_data.append({"monthlyfee": monthlyfee, "extrafeeperpatients": extrafeeperpatients, "noofcycle": noofcycle})
        clinic_data=clinic_data[0]
        #accounts data
        with connection.cursor() as cursor:
            cursor.execute("SELECT startdate FROM clinic WHERE id = %s", (clinicid,))
            accounts_data_tuple = cursor.fetchall()
            accounts_data=[]
            for row in accounts_data_tuple:
                startdate = str(row[0])
                accounts_data.append({"startdate": startdate})
        accounts_data=accounts_data[0]            
        current_month = datetime.now().strftime('%Y-%m')
        current_month_patient_data = [p for p in patient_data if p["vewreportdate"][:7] == current_month]
        total_patients_scanned = sum(p["noofclick"] for p in current_month_patient_data)
        if total_patients_scanned > clinic_data["noofcycle"]:
            amount = clinic_data["monthlyfee"] + ((total_patients_scanned - clinic_data["noofcycle"]) * clinic_data["extrafeeperpatients"])
        else:
            amount = clinic_data["monthlyfee"]
        start_date = datetime.strptime(accounts_data["startdate"], "%Y-%m-%d")
        next_due_date = start_date + timedelta(days=60)
        current_date = datetime.now()
        due_in = (next_due_date - current_date).days
        payment_status = "Unpaid" if due_in > 0 else "Unpaid"
        year, month = current_month.split("-")
        month_name = calendar.month_name[int(month)]
        payment_summary = {
            "amount": amount,
            "due_in": str(due_in)+ ' Days',
            "month": month_name,
            "next_bill_due_date": next_due_date,#here
            "patient_scanned": total_patients_scanned,
            "payment_date":current_date,
            "payment_month": month_name+' '+year,
            "status": payment_status,
            "year":year
        }
        return [payment_summary]
    
    except Exception as e:
        app.logger.error("An error occurred: %s", str(e))
        return jsonify({"success": False, "message": "An error occurred", "error": str(e)}), 500
    

def get_accounts_data_clinic_id(clinic_id):
    try:
        # patient data
        with connection.cursor() as cursor:
            cursor.execute("SELECT email FROM users WHERE clinicid = %s", (clinic_id,))
            emails = cursor.fetchall()
            email_list = [email[0] for email in emails]
        for email in email_list:
            with connection.cursor() as cursor:
                cursor.execute("SELECT vewreportdate,noofclick FROM patient WHERE createdby = %s", (email,))
                patient_data_tuple=cursor.fetchall()
            patient_data = []
            for row in patient_data_tuple:
                vewreportdate = row[0]
                noofclick = row[1]
                if vewreportdate is not None:
                    vewreportdate = vewreportdate.strftime("%Y-%m-%d")
                else:
                    continue
                patient_data.append({"vewreportdate": vewreportdate, "noofclick": noofclick})
        #clinic data
        with connection.cursor() as cursor:
            cursor.execute("SELECT monthlyfee,extrafeeperpatients,noofcycle FROM clinic WHERE id = %s", (clinic_id,))
            clinic_data_tuple = cursor.fetchall()
            clinic_data=[]
            for row in clinic_data_tuple:
                monthlyfee = row[0]
                extrafeeperpatients = row[1]
                noofcycle =row[2]
                clinic_data.append({"monthlyfee": monthlyfee, "extrafeeperpatients": extrafeeperpatients, "noofcycle": noofcycle})
        clinic_data=clinic_data[0]
        #accounts data
        with connection.cursor() as cursor:
            cursor.execute("SELECT startdate FROM clinic WHERE id = %s", (clinic_id,))
            accounts_data_tuple = cursor.fetchall()
            accounts_data=[]
            for row in accounts_data_tuple:
                startdate = str(row[0])
                accounts_data.append({"startdate": startdate})
        accounts_data=accounts_data[0]            
        current_month = datetime.now().strftime('%Y-%m')
        current_month_patient_data = [p for p in patient_data if p["vewreportdate"][:7] == current_month]
        total_patients_scanned = sum(p["noofclick"] for p in current_month_patient_data)
        if total_patients_scanned > clinic_data["noofcycle"]:
            amount = clinic_data["monthlyfee"] + ((total_patients_scanned - clinic_data["noofcycle"]) * clinic_data["extrafeeperpatients"])
        else:
            amount = clinic_data["monthlyfee"]
        start_date = datetime.strptime(accounts_data["startdate"], "%Y-%m-%d")
        next_due_date = start_date + timedelta(days=30)
        current_date = datetime.now()
        due_in = (next_due_date - current_date).days
        payment_status = "Unpaid" if due_in > 0 else "Unpaid"
        year, month = current_month.split("-")
        month_name = calendar.month_name[int(month)]
        print(current_month)
        payment_summary = {
            "amount": amount,
            "due_in": due_in,
            "month": month_name,
            "next_bill_due_date": next_due_date,#here
            "patient_scanned": total_patients_scanned,
            "payment_date":current_date,
            "payment_month": str(current_month),
            "status": payment_status,
            "year":year
        }
        return [payment_summary]
    
    except Exception as e:
        app.logger.error("An error occurred: %s", str(e))
        return jsonify({"success": False, "message": "An error occurred", "error": str(e)}), 500
    
def extract_payment_data():
    print("Running my function...")
    with connection.cursor() as cursor:
        cursor.execute("SELECT id FROM clinic")
        clinic_data = cursor.fetchall()
    clinic_ids = [data[0] for data in clinic_data]
    for clinic_id in clinic_ids:
        print(clinic_id)
        current_date = datetime.now()
        current_month_last_date = current_date.replace(day=calendar.monthrange(current_date.year, current_date.month)[1])
        with connection.cursor() as cursor:
                cursor.execute("SELECT startdate FROM clinic WHERE id = %s", (clinic_id,))
                accounts_data= cursor.fetchall()
                accounts_data=accounts_data[0][0]

        payment_summary_list = get_accounts_data_clinic_id(clinic_id)
        # print(payment_summary_list)
        print(str(current_date)+'---->'+str(current_month_last_date))
        with connection.cursor() as cursor:
                cursor.execute("SELECT startdate FROM clinic WHERE id = %s", (clinic_id,))
                accounts_data= cursor.fetchall()
                accounts_data=accounts_data[0][0]
        start_date = accounts_data.strftime("%Y-%m-%d")
        start_date = datetime.combine(accounts_data, datetime.min.time())
        next_due_date = start_date + timedelta(days=30)
        if current_date > current_month_last_date:
            for payment_summary in payment_summary_list:
                payment_month = payment_summary.get("payment_month")
                patients_canned = payment_summary.get("patient_scanned")
                amount = payment_summary.get("amount")
                status = "Unpaid"

            with connection.cursor() as cursor:
                cursor.execute("SELECT startdate FROM clinic WHERE id = %s", (clinic_id,))
                accounts_data= cursor.fetchall()
                accounts_data=accounts_data[0][0]
            start_date = accounts_data.strftime("%Y-%m-%d")
            start_date = datetime.combine(accounts_data, datetime.min.time())
            next_due_date = start_date + timedelta(days=30)
            previous_month_start_date = start_date + timedelta(days=30)
            startdate = previous_month_start_date.strftime("%Y-%m-%d")
            final_data = {
                "paymentmonth": payment_month,
                "patientscanned": patients_canned,
                "amount": amount,
                "nextbilldate": next_due_date,
                "clinicid": clinic_id,
                "status": status,
                "startdate": startdate
            }
            print(final_data)
            with connection.cursor() as cursor:
                sql = "INSERT INTO accounts (paymentmonth, patientscanned, amount, nextbilldate, clinicid, status, startdate) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                values = (
                    final_data["paymentmonth"],
                    final_data["patientscanned"],
                    final_data["amount"],
                    final_data["nextbilldate"],
                    final_data["clinicid"],
                    final_data["status"],
                    final_data["startdate"]
                )
                cursor.execute(sql, values)
                connection.commit()
        else:
            print('wow')
    email_message()

def email_message():
    with app.app_context():  # Create a Flask app context
        problem_title = 'Test run at 11:30 PM'
        sender_email = 'genesysailabs@gmail.com'
        description = 'test run sucessfull'
        msg = Message(subject=problem_title, sender=sender_email, recipients=['jibingtsr@gmail.com'], body=description)
        mail.send(msg)
    
@app.route('/api/payment', methods=['GET'])
@jwt_required()
def get_payment_info():
    payment_data = {
        "paymentmonth": 'November 2023',
        "patient_scanned": 11,
        "next_bill_due_date": "Mon, 04 Dec 2023 00:00:00 GMT",
        "status": "Unpaid",
        "patients": [
            [
                100658,
                "100001_1test",
                "Jibin George",
                "Fri, 17 Nov 2023 00:00:00 GMT",
                "1",
                "emma@test.com",
                "+917907268722",
                None,
                "Thu, 02 Nov 2023 00:00:00 GMT",
                "Thu, 02 Nov 2023 00:00:00 GMT",
                11
            ],
            [
                100657,
                "100001_CRAFT0001",
                "Ann Thomas",
                "Thu, 30 Mar 2000 00:00:00 GMT",
                "2",
                "emma@test.com",
                "8943071221",
                None,
                "Mon, 30 Oct 2023 00:00:00 GMT",
                "Mon, 30 Oct 2023 00:00:00 GMT",
                2
            ]
        ]
    }
    return jsonify(payment_data)

scheduler = BackgroundScheduler(timezone=timezone('Asia/Kolkata'))
scheduler.add_job(extract_payment_data, 'cron', hour=23, minute=30)
scheduler.start()

# scheduler = BackgroundScheduler()
# scheduler.add_job(email_message, 'interval', seconds=30)
# scheduler.start()


if __name__ == '__main__':
    app.run(debug=False,host='0.0.0.0',threaded=True,port=5001)
