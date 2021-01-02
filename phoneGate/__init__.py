from flask import Flask, request, abort
from twilio.twiml.voice_response import Gather, VoiceResponse
from functools import wraps
from twilio.request_validator import RequestValidator
from twilio.rest import Client
from decouple import config
import logging
import ast
"""
Requires Flask, decouple and Twillio 
"""

TENANT_KEY = False


def create_app():
    # create and configure the app
    app = Flask(__name__)

    print(f'ENV is set to: {app.config["ENV"]}')

    if app.config["ENV"] == "production":
        app.config.from_object("config.ProductionConfig")
    else:
        app.config.from_object("config.DevelopmentConfig")

    # a simple page that says hello
    @app.route('/dev')
    def listValue():
        message = f"Tennants: {app.config['TENANTS']}"
        return message

    def validate_twilio_request(f):
        """Validates that incoming requests genuinely originated from Twilio"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Create an instance of the RequestValidator class
            validator = RequestValidator(app.config['AUTH_TOKEN'])

            # Validate the request using its URL, POST data,
            # and X-TWILIO-SIGNATURE header
            request_valid = validator.validate(
                request.url,
                request.form,
                request.headers.get('X-TWILIO-SIGNATURE', ''))

            # Continue processing the request if it's valid, return a 403 error if
            # it's not
            if request_valid:
                return f(*args, **kwargs)
            else:
                return abort(403)
        return decorated_function

    @app.route("/voice", methods=['GET', 'POST'])
    @validate_twilio_request
    def voice():
        """
        Picks up phone, initiates prompt and send text to tenant
        """

        whitelisted_numbers = app.config["ALLOWED_NUMBERS"]
        caller_number = request.form.get('Caller')

        if caller_number != whitelisted_numbers:
            response = VoiceResponse()
            print("REJECTING THE CALL!!!")
            response.reject()
            return str(response)
        else:
            # Set global key for manipulation
            global TENANT_KEY

            # Reset key value and message the tenants that someone is at the gate
            TENANT_KEY = False
            send_message('Someone is at the gate. Let them in?')
            print("Message sent to tenants")

            # Start Prompt
            response = VoiceResponse()

            # TODO Remove this feature because we cannot protect the traffic between the Guest and the app
            # Using the twillio API
            gather = Gather(action='/verify',
                            finishOnKey='#',
                            input='dtmf',
                            timeout='10'
                            )

            # Setup guest input
            gather.say("Greetings, If you know the code enter it now and press pound. Otherwise, wait for the gatekeepers.",
                       voice='man',
                       language='en-gb',
                       action='/verify'
                       )

            response.append(gather)

            # Added just in case the guest decides to wait
            response.redirect('/verify')
            return str(response)

    @app.route("/verify", methods=['GET', 'POST'])
    def verify():
        # TODO make this more secure by only allowing internal traffic
        print("verification started")
        print(request.headers)
        # Set up voice response instance
        answer = VoiceResponse()

        # We want the tenants to have priority over who is allowed and who is not
        if TENANT_KEY:
            # play the code that opens the gate
            answer.play('', digits='9ww9ww9')
            # tells the tenants that the gate has been opened.
            send_message('The gate that been opened by a gatekeeper.')

        #  Process Digits
        if 'Digits' in request.values:
            # Get which digit the caller chose
            choice = request.values['Digits']

            if choice == app.config['GATE_CODE']:
                answer.play('', digits='9ww9ww9')
                # tells the tenants that the gate has been opened.
                send_message('The gate that been opened by the correct code.')
                return str(answer)

        # If they were not let in, play "You shall not pass! :)"
        answer.play("https://www.myinstants.com/media/sounds/gandalf_shallnotpass.mp3")
        return str(answer)

    @app.route('/sms', methods=['GET', 'POST'])
    @validate_twilio_request
    def incoming_sms():
        """
        Get a reply from the tenants
        """
        # Set global key for manipulation
        global TENANT_KEY
        tenants = app.config["TENANTS"]

        # Get the message and number the user sent our Twilio number
        body = request.values.get('Body', None)
        number = request.values.get('From', None)

        # We noticed that some devices added more than just 'yes'
        # maybe it's extra padding. As long as there is a yes we should
        # open the gate
        if 'yes' in body.lower():
            TENANT_KEY = True
        if 'no' in body.lower():
            TENANT_KEY = False

        # Tell the other tenants who replied with what
        for key, value in tenants.items():
            if value == number:
                message = "{} has replied with {}".format(key, body)
                send_message(message)
                return str(message)

        return "You don't have any Tenants listed"

    def send_message(prompt):

        """
        Sends a text to all the configured tenants.
        """
        # Configure SMS Agent
        account_sid = app.config['ACCOUNT_SID']
        auth_token = app.config['AUTH_TOKEN']
        logging.basicConfig()
        client = Client(account_sid, auth_token)
        client.http_client.logger.setLevel(logging.INFO)

        # retrieve tenants
        tenants = app.config["TENANTS"]

        # Send a message to each of the tenants
        for number in tenants.values():
            message = client.messages.create(
                body=prompt,
                from_=app.config['BOT_NUM'],
                to=number
            )
            return str(message)

        return "You don't have any Tenants listed"

    return app
