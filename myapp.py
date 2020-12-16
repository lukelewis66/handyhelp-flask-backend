# myapp.py

from math import sin, cos, sqrt, atan2, radians
import os
import json
import boto3
from botocore.config import Config
from os.path import join, dirname
import datetime
from flask import Flask, request, jsonify, make_response, redirect
import firebase_admin
from firebase_admin import credentials, firestore, initialize_app
from FirebaseHelpers import getDictFromList
from dotenv import load_dotenv
from decimal import Decimal
load_dotenv(override=True)

# use this if linking to a reaact app on the same server
app = Flask(__name__, static_folder='./build', static_url_path='/')
DEBUG = True

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

# CORS section
@app.after_request
def after_request_func(response):
    if DEBUG:
        print("in after_request")
    origin = request.headers.get('Origin')
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Headers', 'x-csrf-token')
        response.headers.add('Access-Control-Allow-Methods',
                             'GET, POST, OPTIONS, PUT, PATCH, DELETE')
        if origin:
            response.headers.add('Access-Control-Allow-Origin', origin)
    else:
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        if origin:
            response.headers.add('Access-Control-Allow-Origin', origin)

    return response
# end CORS section

session = boto3.Session(
    aws_access_key_id=os.getenv('ACCESS_KEY'),
    aws_secret_access_key=os.getenv('SECRET_KEY'),
    region_name=os.getenv('REGION_NAME'),
)
s3 = session.resource('s3')

@app.route("/bucketinit", methods=['POST'])
def bucketinit():
    if ("UID" in request.form) and ("ACL" in request.form):
        requestUID = request.form['UID']
        requestACL = request.form['ACL']
        s3.create_bucket(
            ACL=f'{requestACL}',
            Bucket=f'{requestUID.lower()}',
            CreateBucketConfiguration={
                'LocationConstraint': 'us-west-1'
            },
        )
        return 'success: bucket initialized', 200
    else:
        return 'failure: no UID or ACL given', 400

@app.route("/upload", methods=['POST'])
def upload():
    if ("UID" in request.form) and ("type" in request.form) and ("IDnum" in request.form):
        uploaded_file = request.files.get('file')
        UID = request.form['UID']
        Type = request.form['type']
        ID = request.form['IDnum']
        key = ''
        if Type == 'ProfilePic':
            key = 'ProfilePic.png'
        elif Type == 'Listing':
            key = 'Listings/' + ID + '/' + uploaded_file.filename
        else:
            key = 'Feed/' + ID + '/' + uploaded_file.filename
        test = s3.Bucket(UID.lower()).put_object(ACL='public-read-write', Key=f'{key}', Body=uploaded_file)
        print("test: ", test)
        return 'success: files uploaded to bucket', 200
    else:
        return 'failure: no UID, type or IDnum given', 400

ENV_KEYS = {
    "type": "service_account",
    "project_id": os.environ['FIREBASE_PROJECT_ID'],
    "private_key_id": os.environ['FIREBASE_PRIVATE_KEY_ID'],
    "private_key": os.environ['FIREBASE_PRIVATE_KEY'].replace("\\n", "\n"),
    "client_email": os.environ['FIREBASE_CLIENT_EMAIL'],
    "client_id": os.environ['FIREBASE_CLIENT_ID'],
    "auth_uri": os.environ['FIREBASE_AUTH_URI'],
    "token_uri": os.environ['FIREBASE_TOKEN_URI'],
    "auth_provider_x509_cert_url": os.environ["FIREBASE_AUTH_PROVIDER_X509_CERT_URL"],
    "client_x509_cert_url": os.environ['FIREBASE_CLIENT_X509_CERT_URL'],
}

cred = credentials.Certificate(ENV_KEYS)
firebase_admin.initialize_app(cred)
db = firestore.client()

# ----------------------------------------------------------------------------------------------------------------
#   ACCOUNT
# ----------------------------------------------------------------------------------------------------------------

@app.route('/checkuserexists', methods=['GET'])
def checkuserexist():
    if "UID" in request.args:
        UID = request.args.get("UID")
        account_ref = db.collection('users').document(UID).get()
        return {"exists": account_ref.exists}, 200
    else:
        return "error", 400

@app.route('/createaccount', methods=['POST'])
def createaccount():
    body = json.loads(request.data)
    if "UID" in body:
        UID = body["UID"]
        data = {
            'name': body["name"],
            'phone': body["phone"],
            'email': body["email"],
            'role': body["role"],
            'location': body["location"],
            'location_string': body["location_string"],
            'date_created': datetime.datetime.now(),
            'active': True,
        }
        new_user_ref = db.collection('users').document(UID)
        new_user_ref.set(data)
        if (body["role"] == "contractor"):
            new_contractor_ref = db.collection('contractors').document(UID)
            contractor_data = {
                'name' : body["name"],
                'bio': "",
                'location_string' : body["location_string"],
                'location' : body["location"],
                'profilepic' : "",
                'skilltags': [],
                'rating' : 0,
                'ratingCount' : 0,
            }
            new_contractor_ref.set(contractor_data)
        return "success", 200
    else:
        return "failure: no UID given", 400

@app.route('/checkuseractive', methods=['GET'])
def checkuseractive():
    if "UID" in request.args:
        UID = request.args.get("UID")
        user_ref = db.collection('users').document(UID).get()
        user = user_ref.to_dict()
        return {"active": user["active"]}, 200
    else:
        return "failure: no UID given", 400

@app.route('/deactivateaccount', methods=['POST'])
def deactivateaccount():
    if "UID" in request.form:
        UID = request.form['UID']
        user_ref = db.collection('users').document(UID)
        user_ref.update({'active': False})
        return "success", 200
    else:
        return "failure: no UID given", 400

@app.route('/reactivateaccount', methods=['POST'])
def reactivateaccount():
    if "UID" in request.form:
        UID = request.form['UID']
        user_ref = db.collection('users').document(UID)
        user_ref.update({'active': True})
        return "success", 200
    else:
        return "failure: no UID given", 400

# ----------------------------------------------------------------------------------------------------------------
#   Review
# ----------------------------------------------------------------------------------------------------------------

@app.route('/getreviews/', methods=['GET'])
def getreviews():
    result = db.collection('reviews').get()
    records = getDictFromList(result)
    return jsonify(records), 200

@app.route('/getavgreview/', methods=['POST'])
def getavgreview():
    body = json.loads(request.data)
    if "UID" in body:
        conUID = body["UID"]
        contractor_ref = db.collection(u'contractors').document(conUID).get()
        contractor = contractor_ref.to_dict()
        rating = float(contractor["rating"])
        return rating, 200
    else:
        return "failure: no UID given", 400

@app.route('/addreview/', methods=['POST'])
def addreview():
    body = json.loads(request.data)
    if ("contractor" in body) and ("client" in body):
        cont = body["contractor"]
        cli = body["client"]
        data = {
            u'contractor': cont,
            u'client': cli,
            u'title': body["title"],
            u'description': body["description"],
            u'rating' : body["rating"],
            u'skilltags': body["skilltags"],
            u'date_posted': datetime.datetime.now(),
        }
        contractor_ref = db.collection(u'contractors').document(cont).get()
        contractor = contractor_ref.to_dict()
        rating = float(body["rating"])
        conrating = float(contractor["rating"])
        count = float(contractor["ratingCount"])
        rating = (((conrating) * count) + rating) / (count + 1)
        count = count + 1
        newcontractor = db.collection(u'contractors').document(cont)
        newcontractor.update({'rating' : rating})
        newcontractor.update({'ratingCount' : count})
        new_review_ref = db.collection(u'reviews').document()
        new_review_ref.set(data)
        return new_review_ref.id, 200
    else:
        return "failure: no contractor or client given", 400 

# ----------------------------------------------------------------------------------------------------------------
#   USER
# ----------------------------------------------------------------------------------------------------------------

@app.route('/getusers/', methods=['GET'])
def getusers():
    result = db.collection('users').get()
    records = getDictFromList(result)
    return jsonify(records), 200

@app.route('/getuser', methods=['GET'])
def getuser():
    if "UID" in request.args:
        UID = request.args.get("UID")
        user = db.collection('users').document(UID).get()
        userDict = user.to_dict()
        return jsonify(userDict), 200
    else:
        return "failure: no UID given", 400

@app.route('/editInfo/', methods=['POST'])
def editInfo():
    if ("UID" in request.form) and ("phone" in request.form) and ("name" in request.form): 
        UID = request.form['UID']
        PHONE = request.form['phone']
        NAME = request.form['name']
        user_ref = db.collection('users').document(UID)
        user_ref.update({'name': NAME})
        user_ref.update({'phone': PHONE})
        return "success", 200
    else:
        return "failure: no UID, phone or name given", 400

@app.route('/getuseremail', methods=['GET'])
def getuseremail():
    if "UID" in request.args:
        UID = request.args.get("UID")
        user_ref = db.collection('users').document(UID).get()
        user = user_ref.to_dict()
        email = user['email']
        return jsonify(email), 200
    else:
        return "failure: no UID given", 400

@app.route('/getusername', methods=['GET'])
def getusername():
    if "UID" in request.args:
        UID = request.args.get("UID")
        user_ref = db.collection('users').document(UID).get()
        user = user_ref.to_dict()
        name = user['name']
        return jsonify(name), 200
    else:
        return "failure: no UID given", 400

# ----------------------------------------------------------------------------------------------------------------
#   LISTING
# ----------------------------------------------------------------------------------------------------------------

@app.route('/addlisting/', methods=['POST'])
def addlisting():
    body = json.loads(request.data)
    if ("active" in body) and ("client" in body):
        data = {
            u'active': body["active"],
            u'client': body["client"],
            u'title': body["title"],
            u'description': body["description"],
            u'images': body["images"],
            u'skilltags': body["skilltags"],
            u'date_posted': datetime.datetime.now(),
        }
        new_listing_ref = db.collection(u'listings').document()
        new_listing_ref.set(data)
        return new_listing_ref.id, 200
    else:
        return "failure: no active or client given", 400

@app.route('/getlistings', methods=['GET'])
def getlistings():
    result = db.collection('listings').order_by('date_posted', direction=firestore.Query.DESCENDING).get()
    listings = getDictFromList(result)
    for key in listings:
        user_ref = db.collection('users').document(listings[key]['client']).get()
        user = user_ref.to_dict()
        if user:
            listings[key]['location_string'] = user['location_string']
            listings[key]['location'] = user['location']
        else:
            listings[key]['location_string'] = ''
            listings[key]['location'] = ''
    return jsonify(listings), 200

@app.route('/updatelistingimages', methods=['POST'])
def updatelistingimages():
    body = json.loads(request.data)
    if ("listingID" in body) and ("imageUrls" in body):
        listingID = body["listingID"]
        imageUrls = body["imageUrls"]
        existing_listing_ref = db.collection(u'listings').document(listingID)
        existing_listing_ref.set({
            "images": imageUrls
        }, merge=True)
        return "success", 200
    else:
        return "failure: no listingID or imageUrls given", 400

@app.route('/deactivatelisting', methods=['POST', 'GET'])
def deactivatelisting():
    if ("LID" in request.form):
        LID = request.form['LID']
        existing_listing_ref = db.collection(u'listings').document(LID)
        existing_listing_ref.update({"active": False})
        return "success", 200
    else:
        return "failure: no LID given", 400

@app.route('/reactivatelisting', methods=['POST', 'GET'])
def reactivatelisting():
    if ("LID" in request.form):
        LID = request.form['LID']
        existing_listing_ref = db.collection(u'listings').document(LID)
        existing_listing_ref.update({"active": True})
        return "success", 200
    else:
        return "failure: no LID given", 400

# ----------------------------------------------------------------------------------------------------------------
# CONTRACTOR
# ----------------------------------------------------------------------------------------------------------------

@app.route('/addfeeditem/', methods=['POST'])
def addfeeditem():
    body = json.loads(request.data)
    if ("contractor" in body) and ("title" in body):
        data = {
            u'contractor': body["contractor"],
            u'title': body["title"],
            u'description': body["description"],
            u'images': body["images"],
            u'skilltags': body["skilltags"],
            u'date_posted': datetime.datetime.now(),
        }
        new_feeditem_ref = db.collection(u'feeds').document() 
        new_feeditem_ref.set(data)
        return new_feeditem_ref.id, 200
    else:
        return "failure: no contractor or title given", 400

@app.route('/updatefeeditemimages', methods=['POST'])
def updatefeeditemimages():
    body = json.loads(request.data)
    if ("feedID" in body) and ("imageUrls" in body): 
        feedID = body["feedID"]
        imageUrls = body["imageUrls"]
        existing_feeditem_ref = db.collection(u'feeds').document(feedID)
        existing_feeditem_ref.set({
            "images": imageUrls
        }, merge=True)
        return "success", 200
    else:
        return "failure: no feedID or imageUrls given", 400

@app.route('/getfeeditems', methods=['GET'])
def getfeed():
    result = db.collection('feeds').get()
    records = getDictFromList(result)
    return jsonify(records), 200

@app.route('/getfeeditem', methods=['GET'])
def getfeeditem():
    if "FID" in request.args:
        FID = request.args.get("FID")
        result = db.collection('feeds').document(FID).get()
        return jsonify(result.to_dict()), 200
    else:
        return "failure: no FID given", 400

@app.route('/deletefeeditem', methods=['POST', 'GET'])
def deletefeeditem():
    if ("UID" in request.form) and ("FID" in request.form):
        UID = request.form['UID'].lower()
        FID = request.form['FID']
        db.collection(u'feeds').document(FID).delete()
        s3_client = boto3.client('s3')
        prefix = "Feed/"+ FID + "/"
        response = s3_client.list_objects_v2(Bucket=UID, Prefix=prefix)
        for object in response['Contents']:
            s3_client.delete_object(Bucket=UID, Key=object['Key'])
        return "success", 200
    else:
        return "failure: no UID or FID given", 400

@app.route('/getcontractors/', methods=['GET'])
def getcontractors():
    result = db.collection('contractors').get()
    records = getDictFromList(result)
    return jsonify(records), 200

@app.route('/getallcontractors', methods=['GET'])
def getallcontractors():
    allUsers = db.collection('users').get()
    allUsersDict = getDictFromList(allUsers)
    delete = [key for key in allUsersDict if allUsersDict[key]
              ['role'] != "contractor"]
    for key in delete:
        del allUsersDict[key]
    for key in allUsersDict:
        contractor_ref = db.collection('contractors').document(
            allUsersDict[key]['id']).get()
        allUsersDict[key].update(contractor_ref.to_dict())
    return jsonify(allUsersDict), 200

@app.route('/addcontractor/', methods=['POST'])
def addcontractor():
    try:
        body = json.loads(request.data)
        data = {
            u'name': body["name"],
            u'email': body["email"],
            u'password': body["password"],
            u'location_string' : body["location_string"],
            u'location' : body["location"],
            u'rating': body["rating"],
            u'ratingCount' : body["rating"],
        }
        newClient = db.collection(u'contractors').document()
        newClient.set(data)
        return jsonify(newClient.id),
    except ValueError:
        return jsonify({"MESSAGE": "JSON load error"}), 405

@app.route('/isClient', methods=['GET'])
def isCLient():
    if "UID" in request.args:
        UID = request.args.get("UID")
        result = db.collection('users').document(UID).get()
        records = getDictFromList(result)
        return jsonify(records), 200
    else:
        return "failure: no UID given", 400

@app.route('/getlisting', methods=['GET'])
def getlisting():
    if "LID" in request.args:
        LID = request.args.get("LID")
        result = db.collection('listings').document(LID).get()
        return jsonify(result.to_dict()), 200
    else:
        return "failure: no LID given", 400

@app.route('/getcontractor', methods=['GET'])
def getcontractor():
    if "UID" in request.args:
        UID = request.args.get("UID")
        user = db.collection('users').document(UID).get()
        contractor = db.collection('contractors').document(UID).get()
        userDict = user.to_dict()
        userDict.update(contractor.to_dict())
        return jsonify(userDict), 200
    else:
        return "failure: no UID given", 400

@app.route('/editContractor/', methods=['POST'])
def editContractor():
    body = json.loads(request.data)
    if "UID" in body:
        UID = body["UID"]
        user_ref = db.collection('users').document(UID)
        contractor_ref = db.collection('contractors').document(UID)
        user_ref.update({'name': body["name"]})
        user_ref.update({'phone': body["phone"]})
        contractor_ref.update({'name': body["name"]})
        contractor_ref.update({'skilltags': body["skilltags"]})
        contractor_ref.update({'bio': body["bio"]})
        imageUrls = body["profilepic"]
        contractor_ref.set({
            "profilepic": imageUrls
        }, merge=True)
        return "success", 200
    else:
        return "failure: no UID given", 400

# ----------------------------------------------------------------------------------------------------------------
# CONTRACTS
# ----------------------------------------------------------------------------------------------------------------

@app.route('/getrole', methods=['GET'])
def getrole():
    if "UID" in request.args:
        UID = request.args.get("UID")
        result = db.collection('users').document(UID).get()
        return jsonify(result.to_dict()), 200
    else:
        return "failure: no UID given", 400

@app.route('/getcontracts', methods=['GET'])
def getcontracts():
    result = db.collection('contracts').get()
    records = getDictFromList(result)
    return jsonify(records), 200

@app.route('/api/getmsg/', methods=['GET'])
def respond():
    # Retrieve the msg from url parameter of GET request
    # and return MESSAGE response (or error or success)
    msg = request.args.get("msg", None)
    if DEBUG:
        print("GET respond() msg: {}".format(msg))
    response = {}
    if not msg:  # invalid/missing message
        response["MESSAGE"] = "no msg key found, please send a msg."
        status = 400
    else:  # valid message
        response["MESSAGE"] = f"Welcome {msg}!"
        status = 200
    # Return the response in json format with status code
    return jsonify(response), status

@app.route('/api/keys/', methods=['POST'])
def postit():
    response = {}
    # only accept json content type
    if request.headers['content-type'] != 'application/json':
        return jsonify({"MESSAGE": "invalid content-type"}), 400
    else:
        try:
            data = json.loads(request.data)
        except ValueError:
            return jsonify({"MESSAGE": "JSON load error"}), 405
    acc = data['acckey']
    sec = data['seckey']
    if DEBUG:
        print("POST: acc={}, sec={}".format(acc, sec))
    if acc:
        response["MESSAGE"] = "Welcome! POST args are {} and {}".format(
            acc, sec)
        status = 200
    else:
        response["MESSAGE"] = "No acckey or seckey keys found, please resend."
        status = 400

    return jsonify(response), status
# Set the base route to be the react index.html

@app.route('/')
def index():
    return "hello!"

def main():
    '''The threaded option for concurrent accesses, 0.0.0.0 host says listen to all network interfaces (leaving this off changes this to local (same host) only access, port is the port listened on -- this must be open in your firewall or mapped out if within a Docker container. In Heroku, the heroku runtime sets this value via the PORT environment variable (you are not allowed to hard code it) so set it from this variable and give a default value (8118) for when we execute locally.  Python will tell us if the port is in use.  Start by using a value > 8000 as these are likely to be available.
    '''
    localport = int(os.getenv("PORT", 8118))
    app.run(threaded=True, host='0.0.0.0', port=localport)

if __name__ == '__main__':
    main()
