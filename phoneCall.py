from flask import Flask, request
from twilio.twiml.voice_response import Gather, VoiceResponse, Say, Play
from twilio.rest import Client
from decouple import config

"""
Requires Flask, decouple and Twillio 
"""
app = Flask(__name__)

KEY = False


def send_message():
    """
    Sends a text to all the configured tenants that someone is at the door.....
    """
    # Configure SMS Agent
    account_sid = config('ACCOUNT_SID')
    auth_token = config('AUTH_TOKEN')
    client = Client(account_sid, auth_token)

    # Configure Tenants
    tenants = [config('ABE_NUM'), config('BRANI_NUM'), config('MARCEL_NUM')]

    # Send a message to each of the tenants
    for user in tenants:
        message = client.messages.create(
            body='Someone is at the gate. Let them in?',
            from_=config('BOT_NUM'),
            to=user
        )

    return str(message)


@app.route("/voice", methods=['GET', 'POST'])
def voice():
    """
    Picks up phone, initiates prompt and send text to tenant
    """

    # message the tenants
    send_message()
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
    # Set global key for manipulation
    global KEY

    print("verification started")

    # Set up answer
    answer = VoiceResponse()

    # We want the tenants to have priority over who is allowed and who is not
    if KEY:
        answer.play('', digits='9ww9ww9')

        # TODO: Add function that tells the tenants that the gate has been opened.

        # after the gate is open, reset KEY
        KEY = False
    else:
        answer.play("https://www.myinstants.com/media/sounds/gandalf_shallnotpass.mp3")

    #  Process Digits
    if 'Digits' in request.values:
        # Get which digit the caller chose
        choice = request.values['Digits']

        if choice == config('GATE_CODE'):
            answer.play('', digits='9ww9ww9')

            # TODO: Add function that tells the tenants that the gate has been opened.

            # after the gate is open, reset KEY
            KEY = False
            return str(answer)

    KEY = False
    return str(answer)


@app.route('/sms', methods=['GET', 'POST'])
def incoming_sms():
    """
    Get a reply from the tenants
    """
    # Set global key for manipulation
    global KEY

    # Get the message the user sent our Twilio number
    body = request.values.get('Body', None)

    # We noticed that some devices added more than just 'yes'
    # maybe it's extra padding. As long as there is a yes we should
    # open the gate
    if 'yes' in body.lower():
        KEY = True
    if 'no' in body.lower():
        KEY = False

    return 'placeholder'


if __name__ == "__main__":
    app.run(debug=True,
            host='0.0.0.0'
            )
