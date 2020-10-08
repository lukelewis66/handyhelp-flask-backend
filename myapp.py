# myapp.py
''' 
    This file is based off of this tutorial: https://stackabuse.com/deploying-a-flask-application-to-heroku/ 
    Author: Chandra Krintz, 
    License: UCSB BSD -- see LICENSE file in this repository
'''

import os, json
from flask import Flask, request, jsonify, make_response

#use this if linking to a reaact app on the same server
#app = Flask(__name__, static_folder='./build', static_url_path='/')
app = Flask(__name__)
DEBUG=True

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
            response.headers.add('Access-Control-Allow-Origin', origin)

    return response
### end CORS section

'''
Note that flask automatically redirects routes without a final slash (/) to one with a final slash (e.g. /getmsg redirects to /getmsg/). Curl does not handle redirects but instead prints the updated url. The browser handles redirects (i.e. takes them). You should always code your routes with both a start/end slash.
'''
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
    return "<h1>Welcome to our server !!</h1>",200

    #use this instead if linking to a raact app on the same server
    #make sure and update the app = Flask(...) line above for the same
    #return app.send_static_file('index.html') 

def main():
    '''The threaded option for concurrent accesses, 0.0.0.0 host says listen to all network interfaces (leaving this off changes this to local (same host) only access, port is the port listened on -- this must be open in your firewall or mapped out if within a Docker container. In Heroku, the heroku runtime sets this value via the PORT environment variable (you are not allowed to hard code it) so set it from this variable and give a default value (8118) for when we execute locally.  Python will tell us if the port is in use.  Start by using a value > 8000 as these are likely to be available.
    '''
    localport = int(os.getenv("PORT", 8118))
    app.run(threaded=True, host='0.0.0.0', port=localport)

if __name__ == '__main__':
    main()
