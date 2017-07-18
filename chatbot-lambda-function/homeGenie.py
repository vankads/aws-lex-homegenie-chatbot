import math
import dateutil.parser
import datetime
import time
import os
import logging
import boto3
import json
import httplib




logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
iotClient = boto3.client('iot')
iotDataClient = boto3.client('iot-data')


""" --- Helpers to build responses which match the structure of the necessary dialog actions --- """


def get_slots(intent_request):
    return intent_request['currentIntent']['slots']


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message, response_card):
    response = {'sessionAttributes': session_attributes,
                'dialogAction': {
                    'type': 'ElicitSlot',
                    'intentName': intent_name,
                    'slots': slots,
                    'slotToElicit': slot_to_elicit,
                    'message': message
                    }
                }
    if response_card:
        response['dialogAction']["responseCard"]=response_card
    print response
    return response


def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }


""" --- Helper Functions --- """


def build_response_card(title, sub_title, things):
    responseCard = {
    "version": 1,
    "contentType": "application/vnd.amazonaws.card.generic", 
    "genericAttachments": [
    	{
    	"title":title,
    	"subTitle":sub_title
        }
    ] }

    buttons=[]
    for i in things:
        button={}
    	button["text"]=i['thingName']
    	button["value"]=i['thingName']
    	buttons.append(button)
    
    responseCard["genericAttachments"][0]["buttons"] = buttons
    
    return responseCard


def build_response_message( message_content):
    return {'contentType': 'PlainText', 'content': message_content}

def search_thing(thing_name):
    
    thingsList = iotClient.list_things()
    for i in thingsList['things']:
        if i['thingName'].lower() == thing_name.lower():
            return i
    
    things = []
    for i in thingsList['things']:
        if i['thingTypeName'] == 'Appliance' and i['attributes']['ApplianceType'].lower() == thing_name.lower():
            things.append(i)
    
    if len(things) == 0:
        return ''
    else:
        return things

""" --- Functions that control the bot's behavior --- """

def list_things(intent_request):
    source = intent_request['invocationSource']
    if source == 'FulfillmentCodeHook':
        thingsList = iotClient.list_things()
        content = 'We found following things in your home \n'
        for i in thingsList['things']:
            
            if i['thingTypeName'] == 'Sensor':
                content = content +  i['thingName']+" "+i['thingTypeName']+'\n'
            else:
                content = content +  i['thingName']+'\n'
        
        return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': content})

def get_thing_state(intent_request):
    """
    Performs dialog management and fulfillment for getting status of a thing.
    Beyond fulfillment, the implementation of this intent demonstrates the use of the elicitSlot dialog action
    in slot validation and re-prompting.
    """

    thing_name = get_slots(intent_request)["thingName"]
    thing_state = get_slots(intent_request)["thingState"]
    source = intent_request['invocationSource']
    slots = get_slots(intent_request)
    
    if source == 'DialogCodeHook':
                
        return validate_thing_name(intent_request)

    if source == 'FulfillmentCodeHook':
        
        thingShadow = iotDataClient.get_thing_shadow(thingName=slots['thingName'])
        jsonState = json.loads(thingShadow["payload"].read())
        print jsonState
        thingState =  jsonState["state"]["reported"]["value"] 
        print thingState
            
        content = '{} is {}'.format(slots['thingName'],thingState)
        if(intent_request['sessionAttributes']['thingTypeName'] == 'Sensor'):
            content= '{} at your home is {}'.format(slots['thingName'],thingState)
        return close(intent_request['sessionAttributes'],
                    'Fulfilled',
                    {'contentType': 'PlainText','content': content})        



def update_thing_state(intent_request):
    """
    Performs dialog management and fulfillment for updating thing status.
    Beyond fulfillment, the implementation of this intent demonstrates the use of the elicitSlot dialog action
    in slot validation and re-prompting.
    """

    thing_name = get_slots(intent_request)["thingName"]
    thing_state = get_slots(intent_request)["thingState"]
    source = intent_request['invocationSource']
    
    if source == 'DialogCodeHook':
                
        return validate_thing_name(intent_request)

    if source == 'FulfillmentCodeHook':

        data = {"state" : { "desired" : { "value" : thing_state }}}
                
        mypayload = json.dumps(data)
        response = iotDataClient.update_thing_shadow(
            thingName = thing_name, 
            payload = mypayload
        )
        jsonState = json.loads(response["payload"].read())
        print jsonState        
        
        broadcast_update(intent_request['userId'],"",thing_name,thing_state)
        
        return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'State of your {} at your home is updated'.format(thing_name)})
                  
def broadcast_update(user_name, channel_name, thing_name, updated_state):
    
    content='State of your {} at your home updated to {}'.format(thing_name, updated_state)
    data = {'text': content}
    headers = {"Content-type": "application/json"}
    conn = httplib.HTTPSConnection("hooks.slack.com")
    # replace following url with actual poastback url
    conn.request("POST", "/services/xxxxxxxxxxxxx", json.dumps(data), headers)
    response = conn.getresponse()
    conn.close() 

def validate_thing_name(intent_request):
    
    thing_name = get_slots(intent_request)["thingName"]
    thing_state = get_slots(intent_request)["thingState"]
    source = intent_request['invocationSource']
    slots = get_slots(intent_request)    
    
    if not slots['thingName'] :
        return delegate(intent_request['sessionAttributes'], slots)
        
    # if not thing_name:
    #     print intent_request['sessionAttributes']
    #     if  intent_request['sessionAttributes'] and 'responseRequested' in intent_request['sessionAttributes']:
    #         print intent_request['sessionAttributes']
    #         intent_request['sessionAttributes'].pop('responseRequested')
    #         print intent_request['sessionAttributes']
    #         thing_name = intent_request['inputTranscript']
    #     else:
    #         return delegate(intent_request['sessionAttributes'], slots)
    
    thing = search_thing(thing_name)
        
    if not thing:
        slots['thingName']=None
        return elicit_slot(intent_request['sessionAttributes'],intent_request['currentIntent']['name'],slots,
                               'thingName',
                               build_response_message("No devices by name {} found".format(thing_name)),'')  
    elif type(thing) is list: 
        print thing
        content = 'There are multiple {}\'s at your home \n'.format(thing_name)
        for i in thing:
            content = content +  i['thingName']+'\n'
        slots['thingName']=None
        # if not intent_request['sessionAttributes']:
        #     intent_request['sessionAttributes']={}
        # intent_request['sessionAttributes']['responseRequested']='Yes'
        return elicit_slot(intent_request['sessionAttributes'],intent_request['currentIntent']['name'],slots,
                                'thingName',
                                 build_response_message(content),build_response_card("Select Device",'Select the smart device',thing))                 
                             
    else:
        if thing['thingTypeName'] == 'Sensor' and intent_request['currentIntent']['name'] == 'UpdateThingState':
            return close(intent_request['sessionAttributes'],'Failed',
                            {'contentType': 'PlainText',
                            'content': 'State of {} cannot be updated'.format(thing['thingName'])})
        slots['thingName']=thing['thingName']
        if not intent_request['sessionAttributes']:
            intent_request['sessionAttributes']={}
        intent_request['sessionAttributes']['thingTypeName']=thing['thingTypeName']
        return delegate(intent_request['sessionAttributes'], slots)    

""" --- Intents --- """


def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """

    logger.debug('dispatch userId={}, intentName={},invocationSource={} '.format(intent_request['userId'], intent_request['currentIntent']['name'], intent_request['invocationSource']))

    intent_name = intent_request['currentIntent']['name']

    # Dispatch to your bot's intent handlers
    
    if intent_name == 'ListThings':
        return list_things(intent_request) 
        
    if intent_name == 'GetThingState':
        return get_thing_state(intent_request)   
        
    if intent_name == 'UpdateThingState':
        return update_thing_state(intent_request)          

    raise Exception('Intent with name ' + intent_name + ' not supported')


""" --- Main handler --- """


def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    print event
    logger.debug('event.bot.name={}'.format(event['bot']['name']))
    
    return dispatch(event)

