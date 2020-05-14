# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
  
#   Licensed under the Apache License, Version 2.0 (the "License").
#   You may not use this file except in compliance with the License.
#   A copy of the License is located at
  
#       http://www.apache.org/licenses/LICENSE-2.0
  
#   or in the "license" file accompanying this file. This file is distributed 
#   on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either 
#   express or implied. See the License for the specific language governing 
#   permissions and limitations under the License.

import json
import boto3
from urllib.parse import unquote_plus
import urllib
import time
import os

translate = boto3.client(service_name='translate', region_name='us-east-1', use_ssl=True)
s3 = boto3.resource('s3')
a2i = boto3.client('sagemaker-a2i-runtime')

flowDefnARN = unquote_plus(os.environ['FLOW_DEF_ARN']) 


def lambda_handler(event, context):
    
    # Get the object from the event
    bucketName = event['Records'][0]['s3']['bucket']['name']
    keyName = unquote_plus(event['Records'][0]['s3']['object']['key'])
    fileName = keyName[keyName.rindex('/')+1:keyName.rindex('.')]

    # Read the S3 Object
    bucket = s3.Bucket(bucketName)
    body = bucket.Object(keyName).get()['Body'].read().decode("utf-8", 'ignore')
    
    # Create the human loop input JSON object
    humanLoopInput = {
        'SourceLanguage' : 'English',
        'TargetLanguage' : 'Spanish',
        'sourceLanguageCode':'en',
        'targetLanguageCode' : 'es',
        'translationPairs' : [],
        'rowCount': 0,
        'bucketName': bucketName,
        'keyName': keyName
    }
    
    translatedText = ''
    rowCount = 0

    print('Splitting file and performing translation')    

    # split the body by period to get individual sentences
    for sentence in body.split('.'):
        if len(sentence.lstrip()) > 0:
            # call translation
            translate_response = translate.translate_text(
                                    Text=sentence + '.',
                                    SourceLanguageCode='en',
                                    TargetLanguageCode='es'
                                )
            
            translatedSentence = translate_response['TranslatedText']

            translationPair = {
                                'originalText': sentence + '.',
                                'translation': translatedSentence
                                }
            humanLoopInput['translationPairs'].append(translationPair)
            rowCount+=1
            translatedText = translatedText + translatedSentence + ' '

    humanLoopInput['rowCount'] = rowCount

    humanLoopName = 'Translate-Medical-Text' + str(int(round(time.time() * 1000)))
    print('Starting human loop - ' + humanLoopName)
    response = a2i.start_human_loop(
                                HumanLoopName=humanLoopName,
                                FlowDefinitionArn= flowDefnARN,
                                HumanLoopInput={
                                    'InputContent': json.dumps(humanLoopInput)
                                    }
                                )
    
    # write the machine translated file to S3 bucket.
    targetKey = ('machine_output/MO-{0}.txt').format(fileName)
    print ('Writing translated text to '+ bucketName + '/' + targetKey)
    object = s3.Object(bucketName, targetKey)
    object.put(Body=translatedText.encode('utf-8'))

    print('Success')
    return 0
