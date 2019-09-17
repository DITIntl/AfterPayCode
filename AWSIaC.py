import logging
import boto3
from operator import itemgetter

"""Exercise create_ec2_instance()"""
client = boto3.client('ec2')
response = client.describe_images(
Filters=[
        {
            'Name': 'description',
            'Values': [
                'Amazon Linux AMI*',
            ]
        },
 ],
 Owners=[
    'amazon'
 ]
)
# Sort on Creation date Desc
image_details = sorted(response['Images'],key=itemgetter('CreationDate'),reverse=True)
ami_id = image_details[0]['ImageId']
logging.basicConfig(format='%(asctime)s %(message)s')
logging.warning('Script will use Amazon AMI ID :  %s for bulding base customized AMI', ami_id)
ec2_client = boto3.client('ec2')
response = ec2_client.run_instances(ImageId=ami_id,
                                            InstanceType='t2.micro',
                                            KeyName='AfterPayKey',
                                            MinCount=1,
                                            MaxCount=1)
    
