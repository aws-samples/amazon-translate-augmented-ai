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
client = boto3.client('s3')

flowDefnARN = unquote_plus(os.environ['FLOW_DEF_ARN']) 
targetBucketName = unquote_plus(os.environ['TARGET_BUCKET_NAME']) 


def lambda_handler(event, context):

    s3location = ''
    if event['detail-type'] == 'SageMaker A2I HumanLoop Status Change':
        if event['detail']['flowDefinitionArn'] == flowDefnARN:
            if event['detail']['humanLoopStatus'] == 'Completed':
                s3location = event['detail']['humanLoopOutput']['outputS3Uri']

    if s3location != '':
        s3location = s3location.replace('s3://', '')
        
        print("Recreating output file with human post edits...")

        # recreate the output text document, including post edits.
        tmsFile = client.get_object(Bucket=s3location[0:s3location.index('/')],
                                    Key=s3location[s3location.index('/') + 1: len(s3location)])['Body'].read()
        tmsFile = json.loads(tmsFile.decode('utf-8'))
        inputContent = tmsFile['inputContent']
        rowcount = inputContent['rowCount']
        answerContent = tmsFile['humanAnswers'][0]['answerContent']
        editedContent = ''
        for index in range(1, rowcount):
            editedContent += (answerContent['translation'+str(index)] + " ")

        print("Human reviewed file object created.")

        # extract the file name
        targetKeyName = inputContent['keyName']
        targetKeyName = targetKeyName[targetKeyName.index('/') + 1: len(targetKeyName)]
       
        print("Saving file to post_edits folder...")

        # save the file.
        client.put_object(Bucket=targetBucketName,
                          Key='post_edits/PO-{0}'.format(targetKeyName),
                        Body=editedContent.encode('utf-8'))
        print("Success.")

    return 0
