HomeGenie is my chatbot which enables me to monitor and control my smart home. Things at my home are classified into two types – Sensors and appliances. 
Sensors help me to monitor various parameters – like temperature, humidity, light and moisture level in my lawn. 
Based on these values I will control my appliances – if temperature is low, I will turn on heater before I reach home. If my lawn is dry, I will turn on my sprinklers even when I am not in town.
 
All these things publish their status to AWS IOT MQTT topics. And their thing shadow gets updated based on these messages.
 
Now if I want to check temperature at my home. I will ask my homegenie chatbot.HomeGenie sends the message to Lex server which interprets my intent and calls configured lambda function to check status of my temperature sensor in thing shadow service and sends the value back to my chatbot.

This project has two modules.
1. aws-iot-device-sdk-java contains code which simulates MQTT messages for things.
2. chatbot-lambda-function contains lambda function in python for chatbot.
 
