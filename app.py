import os
import sys
import json

import requests
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy

from flask_heroku import Heroku

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://localhost/main'
#app.config['SQLALCHEMY_BINDS'] = {
#    'users': 'postgresql://localhost/all-users',
#    'events': 'postgresql://localhost/all-events'
#}
# app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
# heroku = Heroku(app)
db = SQLAlchemy(app)

# Create our database model
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True)
    events = db.relationship('Event', backref='owner')

    def __init__(self, email):
        self.email = email

    def __repr__(self):
        return '<E-mail %r>' % self.email

class Event(db.Model):
    __tablename__ = "events"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(240))
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __init__(self, owner_email, name):
        self.owner_id = User.query.filter(User.email.match(owner_email))[0].id
        self.name = name

    def __repr__(self):
        return '<Name %r> <Owner %r>' % (self.name, self.owner.email)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/users', methods=['GET'])
def users_index():
    return render_template(
       'users.html',
       users=User.query.all())

@app.route('/events', methods=['GET'])
def events_index():
    return render_template(
        'events.html',
        events=Event.query.all())

@app.route('/signup', methods=['GET'])
def signup_index():
    return render_template('signup_index.html')

# Created for testing purposes only
@app.route('/create_event', methods=['GET'])
def create_event_index():
    return render_template('event_signup_index.html')

# Save e-mail to database and send to success page
@app.route('/prereg', methods=['POST'])
def prereg():
    email = None
    if request.method == 'POST':
        email = request.form['email']
        # Check that email does not already exist (not a great query, but works)
        if not db.session.query(User).filter(User.email == email).count():
            reg = User(email)
            db.session.add(reg)
            db.session.commit()
            return render_template('success.html')
    return render_template('index.html')

@app.route('/events_prereg', methods=['POST'])
def events_prereg():
    owner_email = None
    name = None
    if request.method == 'POST':
        owner_email = request.form['owner_email']
        name = request.form['name']
        # Check that the owner is a real user
        if db.session.query(User).filter(User.email == owner_email).count():
            reg = Event(owner_email, name)
            db.session.add(reg)
            db.session.commit()
            return render_template('success.html')
    return render_template('index.html')

@app.route('/facebook/webhook/', methods=['GET'])
def verify():
    # when the endpoint is registered as a webhook, it must echo back
    # the 'hub.challenge' value it receives in the query arguments
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == os.environ["VERIFY_TOKEN"]:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Facebook Webhook URL", 200


@app.route('/facebook/webhook/', methods=['POST'])
def webhook():

    # endpoint for processing incoming messaging events

    data = request.get_json()
    log(data)  # you may not want to log every incoming message in production, but it's good for testing

    if data["object"] == "page":

        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:

                if messaging_event.get("message"):  # someone sent us a message

                    sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                    recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
                    message_text = messaging_event["message"]["text"]  # the message's text

                    if 'hello' in message_text.lower() or 'hi' in message_text.lower() or 'yo' in message_text.lower():
                        send_message(sender_id, "Hello! I'm Salonniere, your go-to intelligent event organizer. How can I help you?")

                    elif'ted' in message_text.lower():
                        send_message(sender_id, "Ted is a god.")

                    else:
                        send_message(sender_id, "idk how to respond to that... o.o")

                if messaging_event.get("delivery"):  # delivery confirmation
                    pass

                if messaging_event.get("optin"):  # optin confirmation
                    pass

                if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
                    pass

    return "ok", 200


def send_message(recipient_id, message_text):

    log("sending message to {recipient}: {text}".format(recipient=recipient_id, text=message_text))

    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        }
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)


def log(message):  # simple wrapper for logging to stdout on heroku
    print str(message)
    sys.stdout.flush()


if __name__ == '__main__':
    app.run(debug=True)
