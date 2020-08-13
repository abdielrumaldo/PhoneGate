
from flask import Flask, request
from twilio.twiml.voice_response import Gather, VoiceResponse, Say, Play
from twilio.rest import Client
from decouple import config

"""
Requires Flask, decouple and twillio 
"""
app = Flask(__name__)

KEY = False


def send_message():
    ''' Sends a text to all the configured tennants that someone is at the door'''
    # Configure SMS Agent
    account_sid = config('ACCOUNT_SID')
    auth_token = config('AUTH_TOKEN')
    client = Client(account_sid, auth_token)

    # Configure Tennants
    tennants = []
    tennants.append(config('ABE_NUM'))
    tennants.append(config('BRANI_NUM'))
    tennants.append(config('MARCEL_NUM'))

    # Send a message to each of the tennants
    for user in tennants:
        message = client.messages.create(
                                body='Someone is at the gate. Let them in?',
                                from_=config('BOT_NUM'),
                                to=user
                            )

    return str(message)


@app.route("/voice", methods=['GET', 'POST'])
def voice():
    """Picks up phone, innitiates prompt and send text to tennant"""

    # message the tennants 
    send_message()
    print("Message sent to tennats")

    # Start Prompt
    response = VoiceResponse()

    gather = Gather(action='/verify', finishOnKey='#', input='dtmf', timeout='5')
    # Setup guest input
    gather.say("Greetings, If you know the code enter it now and press pound. Otherwise, wait for the gatekeepers.", voice='man', language='en-gb', action='/verify')

    response.append(gather)

    response.redirect('/verify')
    return str(response)


@app.route("/verify", methods=['GET', 'POST'])
def verify():
    # Set global key for manipulation
    global KEY

    print("verification started")
    # Set up answer
    answer = VoiceResponse()
    # If Twilio's request to our app included already gathered digits,
    # process them

    if 'Digits' in request.values:
        # Get which digit the caller chose
        choice = request.values['Digits']

        if choice == config('GATE_CODE'):
            answer.play('', digits='9ww9ww9')
            #after the gate is open, reset KEY
            KEY = False   
            return str(answer)
            
    if KEY:
        answer.play('', digits='9ww9ww9')
        # after the gate is open, reset KEY
        KEY = False
    else:
        answer.play("https://www.myinstants.com/media/sounds/gandalf_shallnotpass.mp3")
    
    KEY = False   
    return str(answer)


@app.route('/sms', methods=['GET', 'POST'])
def incoming_sms():
    ''' Get a reply from the tennants'''
    # Set up global
    global KEY

    # Get the message the user sent our Twilio number
    body = request.values.get('Body', None)

    if 'yes' in body.lower():
        KEY = True
    if 'no' in body.lower():
        KEY = False

    return 'placeholder'



if __name__ == "__main__":
    app.run(debug=True)
