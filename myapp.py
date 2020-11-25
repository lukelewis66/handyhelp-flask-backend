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


# boto3 session for any S3 functions
session = boto3.Session(
    aws_access_key_id=os.getenv('ACCESS_KEY'),
    aws_secret_access_key=os.getenv('SECRET_KEY'),
    region_name=os.getenv('REGION_NAME'),
)
s3 = session.resource('s3')

# initializes an empty bucket named after the given UID


@app.route("/bucketinit", methods=['POST', 'GET'])
def bucketinit():
    requestUID = request.form['Bucket']
    requestACL = request.form['ACL']
    s3.create_bucket(
        ACL=f'{requestACL}',
        Bucket=f'{requestUID.lower()}',
        CreateBucketConfiguration={
            'LocationConstraint': 'us-west-1'
        },
    )
    return ''

# uploads given image to the bucket named by the UID


@app.route("/upload", methods=['POST', 'GET'])
def upload():
    uploaded_file = request.files.get('file')
    UID = request.form['bucket']
    Type = request.form['type']
    ID = request.form['IDnum']
    key = ''
    if Type == 'ProfilePic':
        key = 'ProfilePic.png'
    elif Type == 'Listing':
        key = 'Listings/' + ID + '/' + uploaded_file.filename
    else:
        key = 'Listings/' + request.form['type'] + '/' + uploaded_file.filename
    s3.Bucket(UID.lower()).put_object(
        ACL='public-read-write', Key=f'{key}', Body=uploaded_file)
    return ''


# cred = credentials.Certificate("handyhelp-f4192-firebase-adminsdk-hgsp6-cbe87ca6a8.json")
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
            'bio': "",
            'profilepic': "",
            'skilltags': [],
            'rating' : 0,
            'ratingCount' : 0,
        }
        new_contractor_ref.set(contractor_data)
    return "success", 200


@app.route('/checkuseractive', methods=['GET'])
def checkuseractive():
    if "UID" in request.args:
        UID = request.args.get("UID")
        user_ref = db.collection('users').document(UID).get()
        user = user_ref.to_dict()
        return {"active": user["active"]}, 200
    else:
        return "error", 400


@app.route('/deactivateaccount', methods=['POST'])
def deactivateaccount():
    UID = request.form['UID']
    # body = json.loads(request.data)
    # UID = body["UID"]
    user_ref = db.collection('users').document(UID)
    user_ref.update({'active': False})
    return "success", 200


@app.route('/reactivateaccount', methods=['POST'])
def reactivateaccount():
    UID = request.form['UID']
    # body = json.loads(request.data)
    # UID = body["UID"]
    user_ref = db.collection('users').document(UID)
    user_ref.update({'active': True})
    return "success", 200



# ----------------------------------------------------------------------------------------------------------------
#   Review
# ----------------------------------------------------------------------------------------------------------------

@app.route('/getreviews/', methods=['GET'])
def getreviews():
    result = db.collection('reviews').get()
    records = getDictFromList(result)
    # test for gitignore
    return jsonify(records), 200

@app.route('/getavgreview/', methods=['POST'])
def getavgreview():
    body = json.loads(request.data)
    conUID = body["UID"]
    contractor_ref = db.collection(u'contractors').document(conUID).get()
    contractor = contractor_ref.to_dict()
    rating = float(contractor["rating"])
    return rating

@app.route('/addreview/', methods=['POST'])
def addreview():
    body = json.loads(request.data)
    print(body)
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
    # get the auto generated document id
    
    contractor_ref = db.collection(u'contractors').document(cont).get()
    contractor = contractor_ref.to_dict()
    rating = float(body["rating"])
    conrating = float(contractor["rating"])
    count = float(contractor["ratingCount"])
    rating = (((conrating) * count) + rating) / (count + 1)
    count = count + 1
    print("rating: ")
    print(rating)
    print("count: ") 
    print(count)
    newcontractor = db.collection(u'contractors').document(cont)
    newcontractor.update({'rating' : rating})
    newcontractor.update({'ratingCount' : count})
    new_review_ref = db.collection(u'reviews').document()
    new_review_ref.set(data)
    return new_review_ref.id, 200
# ----------------------------------------------------------------------------------------------------------------
#   USER
# ----------------------------------------------------------------------------------------------------------------


@app.route('/getusers/', methods=['GET'])
def getusers():
    result = db.collection('users').get()
    records = getDictFromList(result)
    print(records)
    return jsonify(records), 200


@app.route('/getuser', methods=['GET'])
def getuser():
    UID = request.args.get("UID")
    print("UID: ", UID)
    user = db.collection('users').document(UID).get()
    userDict = user.to_dict()
    return jsonify(userDict), 200


@app.route('/editInfo/', methods=['POST'])
def editInfo():
    UID = request.form['UID']
    PHONE = request.form['phone']
    NAME = request.form['name']
    # body = json.loads(request.data)
    # UID = body["UID"]
    user_ref = db.collection('users').document(UID)
    user_ref.update({'name': NAME})
    user_ref.update({'phone': PHONE})
    return "success", 200
# ----------------------------------------------------------------------------------------------------------------
#   LISTING
# ----------------------------------------------------------------------------------------------------------------


@app.route('/addlisting/', methods=['POST'])
def addlisting():
    body = json.loads(request.data)
    data = {
        u'active': body["active"],
        u'client': body["client"],
        u'title': body["title"],
        u'description': body["description"],
        u'images': body["images"],
        u'skilltags': body["skilltags"],
        u'date_posted': datetime.datetime.now(),
    }
    # get the auto generated document id
    new_listing_ref = db.collection(u'listings').document()
    new_listing_ref.set(data)
    return new_listing_ref.id, 200

# @app.route('/getclientlistings', methods=['GET'])
# def getclientlistings():
#     body = json.loads(request.data)
#     UID = body["UID"]
#     result = db.collection('listings').get()
#     records = getDictFromList(result)


@app.route('/getlistings', methods=['GET'])
def getlistings():
    result = db.collection('listings').get()
    records = getDictFromList(result)
    # test for gitignore
    return jsonify(records), 200


@app.route('/updatelistingimages', methods=['POST'])
def updatelistingimages():
    body = json.loads(request.data)
    listingID = body["listingID"]
    imageUrls = body["imageUrls"]
    existing_listing_ref = db.collection(u'listings').document(listingID)
    existing_listing_ref.set({
        "images": imageUrls
    }, merge=True)
    return "success", 200


# ----------------------------------------------------------------------------------------------------------------
# CONTRACTOR
# ----------------------------------------------------------------------------------------------------------------



@app.route('/addfeeditem/', methods=['POST'])
def addfeeditem():
    body = json.loads(request.data)
    data = {
        u'contractor': body["contractor"],
        u'title': body["title"],
        u'description': body["description"],
        u'images': body["images"],
        u'skilltags': body["skilltags"],
        u'date_posted': datetime.datetime.now(),
    }
    new_feeditem_ref = db.collection(u'feeds').document() #get the auto generated document id
    new_feeditem_ref.set(data)
    return new_feeditem_ref.id, 200

@app.route('/updatefeeditemimages', methods=['POST'])
def updatefeeditemimages():
    body = json.loads(request.data)
    feedID = body["feedID"]
    imageUrls = body["imageUrls"]
    existing_feeditem_ref = db.collection(u'feeds').document(feedID)
    existing_feeditem_ref.set({
        "images": imageUrls
    }, merge=True)
    return "success", 200

@app.route('/getfeeditems', methods=['GET'])
def getfeed():
    result = db.collection('feeds').get()
    records = getDictFromList(result)
    #test for gitignore
    return jsonify(records), 200

@app.route('/getfeeditem', methods=['GET'])
def getfeeditem():
    FID = request.args.get("FID")
    print(FID)
    result = db.collection('feeds').document(FID).get()
    print(type(result.to_dict()))
    #test for gitignore
    return jsonify(result.to_dict()), 200

@app.route('/getcontractors/', methods=['GET'])
def getcontractors():
    result = db.collection('contractors').get()
    records = getDictFromList(result)
    return jsonify(records), 200


@app.route('/getallcontractors', methods=['GET'])
def getallcontractors():
    allUsers = db.collection('users').get()
    allUsersDict = getDictFromList(allUsers)
    print("ALl users dict before: ", allUsersDict)
    delete = [key for key in allUsersDict if allUsersDict[key]
              ['role'] != "contractor"]
    for key in delete:
        del allUsersDict[key]
    print(allUsersDict)
    for key in allUsersDict:
        contractor_ref = db.collection('contractors').document(
            allUsersDict[key]['id']).get()
        # contractor_ref = db.collection('contractors').document(user['id']).get()
        allUsersDict[key].update(contractor_ref.to_dict())
    return jsonify(allUsersDict)


@app.route('/addcontractor/', methods=['POST'])
def addcontractor():
    try:
        body = json.loads(request.data)
        data = {
            u'name': body["name"],
            u'email': body["email"],
            u'password': body["password"],
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
    UID = request.args.get("UID")
    result = db.collection('users').document(UID).get()
    records = getDictFromList(result)
    return jsonify(records), 200


@app.route('/getlisting', methods=['GET'])
def getlisting():
    LID = request.args.get("LID")
    print(LID)
    result = db.collection('listings').document(LID).get()
    print(type(result.to_dict()))
    # test for gitignore

    return jsonify(result.to_dict()), 200


@app.route('/getcontractor', methods=['GET'])
def getcontractor():
    UID = request.args.get("UID")
    print("UID for getcontractor: ", UID)
    user = db.collection('users').document(UID).get()
    contractor = db.collection('contractors').document(UID).get()
    userDict = user.to_dict()
    userDict.update(contractor.to_dict())
    #result = db.collection('contractors').document(UID).get()
    # test for gitignore

    return jsonify(userDict), 200


@app.route('/editContractor/', methods=['POST'])
def editContractor():
    body = json.loads(request.data)
    UID = body["UID"]
    user_ref = db.collection('users').document(UID)
    contractor_ref = db.collection('contractors').document(UID)
    # db.contractor_ref.update({UID}, {$set: {'name': data.name}})
    user_ref.update({'name': body["name"]})
    user_ref.update({'phone': body["phone"]})
    contractor_ref.update({'skilltags': body["skilltags"]})
    contractor_ref.update({'bio': body["bio"]})


@app.route('/updateprofilepicture', methods=['POST'])
def updateprofilepicture():
    body = json.loads(request.data)
    UID = body["UID"]
    imageUrls = body["imageUrls"]
    existing_profilepicture_ref = db.collection('contractors').document(UID)
    existing_profilepicture_ref.set({
        "profilepic": imageUrls
    }, merge=True)

    return "success", 200

# ----------------------------------------------------------------------------------------------------------------
# CONTRACTS
# ----------------------------------------------------------------------------------------------------------------


@app.route('/getrole', methods=['GET'])
def getrole():
    UID = request.args.get("UID")
    print("UID :" + UID)
    result = db.collection('users').document(UID).get()
    print(result.to_dict())
    # test for gitignore

    return jsonify(result.to_dict()), 200


@app.route('/getcontracts', methods=['GET'])
def getcontracts():
    result = db.collection('contracts').get()
    records = getDictFromList(result)
    return jsonify(records), 200


# @app.route('/getdistance', methods=['GET'])
# def getdistance():


#     try:
#         UID1 = request.args.get("UID1")
#         UID2 = request.args.get("UID2")
#         print("UID1: " + UID1 + " | UID2: " + UID2)
#         user = db.collection('users').document(UID1).get()
#         other = db.collection('contractors').document(UID2).get()
#         lon1 = user.location[0]
#         lat1 = user.location[1]
#         lon2 = other.location[0]
#         lat2 = other.location[1]
#     except:
#         return jsonify(-1), 200

#     origin = new google.maps.LatLng(lat1, lon1);
#     destination = new google.maps.LatLng(lat2, lon2);

#     service = new google.maps.DistanceMatrixService();
#     service.getDistanceMatrix(
#     {
#     origins: [origin1, origin2],
#     destinations: [destinationA, destinationB],
#     travelMode: 'DRIVING',
#     transitOptions: TransitOptions,
#     drivingOptions: DrivingOptions,
#     unitSystem: UnitSystem,
#     avoidHighways: Boolean,
#     avoidTolls: Boolean,
#     }, callback);

# function callback(response, status) {
#   print("geoDistance response:" + respose + " | status: " + status)
# }


#     print("[" + lat1 + "," + lon1 + "] => [" + lat2 + "," + lon2 + "]")


#     print("\n\nMiles:", distance)

#     return {"distance" : distance}, 200


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
