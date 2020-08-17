from flask import Flask, request
from twilio.twiml.voice_response import Gather, VoiceResponse, Say, Play
from twilio.rest import Client
from decouple import config
import ast

"""
Requires Flask, decouple and Twillio 
"""
app = Flask(__name__)

TENANT_KEY = False

@app.route("/voice", methods=['GET', 'POST'])
def voice():
    """
    Picks up phone, initiates prompt and send text to tenant
    """
    # Set global key for manipulation
    global TENANT_KEY

    # Reset key value and message the tenants that someone is at the gate
    TENANT_KEY = False
    send_message('Someone is at the gate. Let them in?')
    print("Message sent to tenants")

    # Start Prompt
    response = VoiceResponse()

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

    print("verification started")

    # Set up answer
    answer = VoiceResponse()

    # We want the tenants to have priority over who is allowed and who is not
    if TENANT_KEY:
        answer.play('', digits='9ww9ww9')
        # tells the tenants that the gate has been opened.
        send_message('The gate that been opened by a gatekeeper.')

    #  Process Digits
    if 'Digits' in request.values:
        # Get which digit the caller chose
        choice = request.values['Digits']

        if choice == config('GATE_CODE'):
            answer.play('', digits='9ww9ww9')
            # tells the tenants that the gate has been opened.
            send_message('The gate that been opened by the correct code.')
            return str(answer)

    # If they were not let in, play "You shall not pass! :)"
    answer.play("https://www.myinstants.com/media/sounds/gandalf_shallnotpass.mp3")
    return str(answer)


@app.route('/sms', methods=['GET', 'POST'])
def incoming_sms():
    """
    Get a reply from the tenants
    """
    # Set global key for manipulation
    global TENANT_KEY
    tenants = ast.literal_eval(config("TENANTS"))

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

    return 'placeholder'


def send_message(prompt):
    """
    Sends a text to all the configured tenants.
    """
    # Configure SMS Agent
    account_sid = config('ACCOUNT_SID')
    auth_token = config('AUTH_TOKEN')
    client = Client(account_sid, auth_token)

    # retrieve tenants
    tenants = ast.literal_eval(config("TENANTS"))

    # Send a message to each of the tenants
    for number in tenants.values():
        message = client.messages.create(
            body=prompt,
            from_=config('BOT_NUM'),
            to=number
        )

    return str(message)


if __name__ == "__main__":
    app.run(debug=True,
            host='0.0.0.0'
            )
