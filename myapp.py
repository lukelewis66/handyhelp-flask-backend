# myapp.py
''' 
    This file is based off of this tutorial: https://stackabuse.com/deploying-a-flask-application-to-heroku/ 
    Author: Chandra Krintz, 
    License: UCSB BSD -- see LICENSE file in this repository
'''

import os, json
from os.path import join, dirname
from dotenv import load_dotenv
import datetime
from flask import Flask, request, jsonify, make_response
import os, json, boto3
from flask import Flask, request, jsonify, make_response, redirect
import firebase_admin
from firebase_admin import credentials, firestore, initialize_app
from FirebaseHelpers import getDictFromList

#use this if linking to a reaact app on the same server
app = Flask(__name__, static_folder='./build', static_url_path='/')
DEBUG=True

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

### CORS section
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
            print("here!")
            response.headers.add('Access-Control-Allow-Origin', origin)

    return response
### end CORS section

'''
Note that flask automatically redirects routes without a final slash (/) to one with a final slash (e.g. /getmsg redirects to /getmsg/). Curl does not handle redirects but instead prints the updated url. The browser handles redirects (i.e. takes them). You should always code your routes with both a start/end slash.
'''



### uploads given image to the bucket
@app.route("/upload", methods=['POST', 'GET'])
def upload():
    uploaded_file = request.files.get('file')
    if request.method == "POST":
        session = boto3.Session(
            aws_access_key_id=os.environ['ACCESS_KEY'],
            aws_secret_access_key=os.environ['SECRET_KEY'],
            region_name='us-west-1',
        )

        s3 = session.resource('s3')

        s3.Bucket('handyhelpimages').put_object(Key=f'{uploaded_file.filename}', Body=uploaded_file)

        return ''

cred = credentials.Certificate("handyhelp-f4192-firebase-adminsdk-hgsp6-cbe87ca6a8.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

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
    new_listing_ref = db.collection(u'listings').document() #get the auto generated document id
    new_listing_ref.set(data)
    return new_listing_ref.id, 200

@app.route('/getlistings', methods=['GET'])
def getlistings():
    result = db.collection('listings').get()
    records = getDictFromList(result)
    #test for gitignore
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
#   CLIENT
# ----------------------------------------------------------------------------------------------------------------
@app.route('/getclients/', methods=['GET'])
def getclients():
    result = db.collection('clients').get()
    records = getDictFromList(result)
    return jsonify(records), 200

@app.route('/addclient', methods=['POST'])
def addclient():
    try:
        data = json.loads(request.data)
    except ValueError:
        return jsonify({"MESSAGE": "JSON load error"}),405

@app.route('/testgetclients', methods=['GET'])
def testgetclients():
    clients_ref = db.collection('clients')
    all_clients = [doc.to_dict() for doc in clients_ref.stream()]
    return jsonify(all_clients)


# ----------------------------------------------------------------------------------------------------------------
# CONTRACTOR
# ----------------------------------------------------------------------------------------------------------------
@app.route('/getcontractors/', methods=['GET'])
def getcontractors():
    result = db.collection('contractors').get()
    records = getDictFromList(result)
    return jsonify(records), 200

@app.route('/getreviews', methods=['GET'])
def getreviews():
    result = db.collection('reviews').get()
    records = getDictFromList(result)
    return jsonify(records), 200

# ----------------------------------------------------------------------------------------------------------------
# CONTRACTS
# ----------------------------------------------------------------------------------------------------------------

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
    if not msg: #invalid/missing message
        response["MESSAGE"] = "no msg key found, please send a msg."
        status = 400
    else: #valid message
        response["MESSAGE"] = f"Welcome {msg}!"
        status = 200

    # Return the response in json format with status code
    return jsonify(response), status

@app.route('/api/keys/', methods=['POST']) 
def postit(): 
    '''
    Implement a POST api for key management.
    Note that flask handles request.method == OPTIONS for us automatically -- and calls after_request_func (above)after each request to satisfy CORS
    '''
    response = {}
    #only accept json content type
    if request.headers['content-type'] != 'application/json':
        return jsonify({"MESSAGE": "invalid content-type"}),400
    else:
        try:
            data = json.loads(request.data)
        except ValueError:
            return jsonify({"MESSAGE": "JSON load error"}),405
    acc = data['acckey']
    sec = data['seckey']
    if DEBUG:
        print("POST: acc={}, sec={}".format(acc,sec))
    if acc:
        response["MESSAGE"]= "Welcome! POST args are {} and {}".format(acc,sec)
        status = 200
    else:
        response["MESSAGE"]= "No acckey or seckey keys found, please resend."
        status = 400

    return jsonify(response), status

# Set the base route to be the react index.html
@app.route('/')
def index():
    
    return app.send_static_file('index.html') 

def main():
    '''The threaded option for concurrent accesses, 0.0.0.0 host says listen to all network interfaces (leaving this off changes this to local (same host) only access, port is the port listened on -- this must be open in your firewall or mapped out if within a Docker container. In Heroku, the heroku runtime sets this value via the PORT environment variable (you are not allowed to hard code it) so set it from this variable and give a default value (8118) for when we execute locally.  Python will tell us if the port is in use.  Start by using a value > 8000 as these are likely to be available.
    '''
    localport = int(os.getenv("PORT", 8118))
    app.run(threaded=True, host='0.0.0.0', port=localport)

if __name__ == '__main__':
    main()