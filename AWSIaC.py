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
#instance = ec2_resource.create_instances(ImageId=ami_id,
#                                            InstanceType='t2.micro',
#                                            KeyName='AfterPayKey',
#                                            MinCount=1,
#                                            MaxCount=1,
#                                            UserData=user_data_script)


logging.warning('Update packages, install services and configure services on AWSLinuxAfterPay AMI')
#time.sleep(300)
#image = boto3.client('ec2').create_image(InstanceId=instance[0].instance_id, Name='AWSLinuxAfterPay')

#time.sleep(150)


logging.warning('Customised AMI Created for AfterPay')


#ec2server = ec2_resource.create_instances(ImageId=image['ImageId'],
#                                            InstanceType='t2.micro',
#                                            KeyName='AfterPayKey',
#                                            MinCount=1,
#                                            MaxCount=1)



#ec2 = boto3.client('ec2')

#response = ec2.describe_vpcs()
#vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')

#response = ec2.create_security_group(GroupName='ALLOW_SSH_HTTP',
#                                         Description='Allow ssh traffic and web',
#                                         VpcId=vpc_id)
#security_group_id = response['GroupId']
#print('Security Group Created %s in vpc %s.' % (security_group_id, vpc_id))
#data = ec2.authorize_security_group_ingress(
#        GroupId=security_group_id,
#        IpPermissions=[
#            {'IpProtocol': 'tcp',
#             'FromPort': 80,
#             'ToPort': 80,
#             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
#            {'IpProtocol': 'tcp',
#             'FromPort': 22,
#             'ToPort': 22,
#             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
#        ])

user_data_script2= """#!/bin/bash
mkdir myproject
cd myproject
python3 -m venv venv
. venv/bin/activate
sudo pip install Flask
wget https://raw.githubusercontent.com/AfterpayTouch/recruitment-challenge-1/master/tiny_app.py
export FLASK_APP=tiny_app.py
sed -i "s/app.run()/app.run(host='0.0.0.0', debug=True, port=80)/g" tiny_app.py
sudo python tiny_app.py"""


#ec2server = ec2_resource.create_instances(ImageId='ami-009eb83aa92b90a96',
#                                            InstanceType='t2.micro',
#                                            KeyName='AfterPayKey',
#                                            MinCount=1,
#                                            MaxCount=1,
#					    SecurityGroupIds=[
#            					security_group_id,
#            				    ],
#					    UserData=user_data_script2)




ec2server = ec2_resource.create_instances(ImageId='ami-009eb83aa92b90a96',
                                            InstanceType='t2.micro',
                                            KeyName='AfterPayKey',
                                            MinCount=1,
                                            MaxCount=1,
                                            SecurityGroupIds=[
                                                'sg-0d33a50e7c4878f36',
                                            ],
                                            UserData=user_data_script2)

time.sleep(120)

client = boto3.client('autoscaling')

#response = client.create_launch_configuration(
#    ImageId='ami-009eb83aa92b90a96',
#    LaunchConfigurationName='LaunchConfig01',
#    InstanceId='i-0996e316ac8b41114',
#    UserData=user_data_script2,
#    InstanceType='t2.micro',

#    SecurityGroups=[
#        'sg-0d33a50e7c4878f36',
#    ],
#)

#response = client.create_auto_scaling_group(
#    AutoScalingGroupName='AutoScaleGroup01',
#    InstanceId=ec2server[0].instance_id,
#    DesiredCapacity=2,
#    MaxSize=2,
#    MinSize=2
#)

#response = client.attach_instances(
#    InstanceIds=[
#        ec2server[0].instance_id,
#    ],
#    AutoScalingGroupName='AutoScaleGroup01'
#)

client = boto3.client('elb')
response = client.create_load_balancer(
    Listeners=[
        {
            'InstancePort': 80,
            'InstanceProtocol': 'HTTP',
            'LoadBalancerPort': 80,
            'Protocol': 'HTTP',
        },
    ],
    LoadBalancerName='AWS-ELB-01',
    SecurityGroups=[
        'sg-0d33a50e7c4878f36',
    ],
    Subnets=[
        ec2server[0].subnet_id,
    ],
)

print(response['DNSName'])


client = boto3.client('autoscaling')

response = client.create_auto_scaling_group(
    AutoScalingGroupName='AutoScaleGroup01',
    InstanceId=ec2server[0].instance_id,
    DesiredCapacity=2,
    MaxSize=2,
    MinSize=2
)

response = client.attach_load_balancers(
    AutoScalingGroupName='AutoScaleGroup01',
    LoadBalancerNames=[
        'AWS-ELB-01',
    ]
)
