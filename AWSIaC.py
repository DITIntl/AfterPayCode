import time
import logging
import boto3
from operator import itemgetter

"""Exercise create_ec2_instance()"""
client = boto3.client('ec2')

filters = [ {
    'Name': 'name',
    'Values': ['amzn-ami-hvm-*']
},{
    'Name': 'description',
    'Values': ['Amazon Linux AMI*']
},{
    'Name': 'architecture',
    'Values': ['x86_64']
},{
    'Name': 'owner-alias',
    'Values': ['amazon']
},{
    'Name': 'state',
    'Values': ['available']
},{
    'Name': 'root-device-type',
    'Values': ['ebs']
},{
    'Name': 'virtualization-type',
    'Values': ['hvm']
},{
    'Name': 'hypervisor',
    'Values': ['xen']
},{
    'Name': 'image-type',
    'Values': ['machine']
} ]

# Use above filters 
response = client.describe_images(
  Filters=filters,
  Owners=[
      'amazon'
  ]
)

# Sort on Creation date Desc
image_details = sorted(response['Images'],key=itemgetter('CreationDate'),reverse=True)
ami_id = image_details[0]['ImageId']
logging.basicConfig(format='%(asctime)s %(message)s')

logging.warning('Script will use Amazon AMI ID :  %s for bulding base customized AMI', ami_id)


#ec2 = boto3.client('ec2')
#response = ec2.create_key_pair(KeyName='AfterPayKey2')
logging.warning('Generating a SSH-key file AfterPayKey.pem whcih can be used to loggin to server ')

#f= open("AfterPayKey2.pem","w+")
#f.write(str(response))
#f.close()

logging.warning('Creating a customised AMI ...')

user_data_script = """#!/bin/bash
sudo yum -y update --security
sudo yum -y update
sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1
sudo sysctl -w net.ipv6.conf.default.disable_ipv6=1
sudo yum -y install ntp
sudo yum -y install telnet
sudo yum -y install mtr
sudo yum -y install tree
sudo systemctl start ntpd
sudo systemctl enable ntpd.service
echo "*         hard    nofile      65535" | sudo tee -a /etc/security/limits.conf
echo "*         soft    nofile      65535" | sudo tee -a /etc/security/limits.conf"""

ec2_resource = boto3.resource('ec2')
instance = ec2_resource.create_instances(ImageId=ami_id,
                                            InstanceType='t2.micro',
                                            KeyName='AfterPayKey',
                                            MinCount=1,
                                            MaxCount=1,
                                            UserData=user_data_script)


logging.warning('Update packages, install services and configure services on AWSLinuxAfterPay AMI')
time.sleep(300)
image = boto3.client('ec2').create_image(InstanceId=instance[0].instance_id, Name='AWSLinuxAfterPay')

time.sleep(150)


logging.warning('Customised AMI Created for AfterPay')


ec2server = ec2_resource.create_instances(ImageId=image['ImageId'],
                                            InstanceType='t2.micro',
                                            KeyName='AfterPayKey',
                                            MinCount=1,
                                            MaxCount=1)
