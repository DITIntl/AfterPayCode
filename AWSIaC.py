import time
import logging
import boto3
from operator import itemgetter


#########  Create a filter to filter out Amazon Linux standard base image, which will be used to build customized AMI for AfterPay. #########

findAmiClient = boto3.client('ec2')

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

######### Use above filter to search in Amazon for AMI ID ############ 
findAmiResponse = findAmiClient.describe_images(
  Filters=filters,
  Owners=[
      'amazon'
  ]
)

######### Sort on above results and creation AMI images on decending order. ###########

image_details = sorted(findAmiResponse['Images'],key=itemgetter('CreationDate'),reverse=True)
amiId = image_details[0]['ImageId']
logging.basicConfig(format='%(asctime)s %(message)s')


logging.warning('Script will use Amazon AMI ID : %s which will be used for  building base customized AMI for AfterPay', amiId)

######## Creating Key Pair and saving it on local computer ##########


sshKeyClient = boto3.client('ec2')
sshKeyResponse = sshKeyClient.create_key_pair(KeyName='AfterPaySSHKey')
logging.warning('Generated a SSH-key file AfterPaySSHKey.pem whcih can be used to login to server and saved it on local folder used to run this script.')

f= open("AfterPaySSHKey.pem","w+")
f.write(str(sshKeyResponse['KeyMaterial']))
f.close()

######## Creating an customized AMI as for the requirement given by AfterPay ######## 

printSpec = """Creating a customized AMI for After pay with below specifications


*All packages are update to date and all pending security updates are applied against the default OS repositories.

*disable IPv6 system wide.

*install the following packages: ntp (NTP daemon)(make sure it is started at boot), telnet, mtr, tree.

*set the max "open files" limit across all users/processes, soft & hard, to 65535.

"""

logging.warning(printSpec)
logging.warning('Creating a customized AMI for AfterPay...')


userDataScriptAmi = """#!/bin/bash
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
echo "*         soft    nofile      65535" | sudo tee -a /etc/security/limits.conf
echo "net.ipv6.conf.all.disable_ipv6 = 1" | sudo tee -a /etc/sysctl.conf
echo "net.ipv6.conf.default.disable_ipv6 = 1" | sudo tee -a /etc/sysctl.conf
echo "net.ipv6.conf.lo.disable_ipv6 = 1" | sudo tee -a /etc/sysctl.conf"""

ec2AmiResource = boto3.resource('ec2')
ec2InstanceAmi = ec2AmiResource.create_instances(ImageId=amiId,
                                            InstanceType='t2.micro',
                                            KeyName='AfterPaySSHKey',
                                            MinCount=1,
                                            MaxCount=1,
                                            UserData=userDataScriptAmi)


logging.warning('Updatinge packages, installing services and configuring services in progress for customized AMI for AfterPay ...')


checkStatusClient = boto3.client('ec2')
ec2AmiStatus = checkStatusClient.describe_instance_status(InstanceIds=[
        			   ec2InstanceAmi[0].instance_id,
    				])

while len(ec2AmiStatus['InstanceStatuses']) == 0:
	ec2AmiStatus = checkStatusClient.describe_instance_status(InstanceIds=[
                                   ec2InstanceAmi[0].instance_id,
                                ]) 
#print(ec2AmiStatus['InstanceStatuses'][0]['InstanceState']['Name'])

time.sleep(30)

amiImage = boto3.client('ec2').create_image(InstanceId=ec2InstanceAmi[0].instance_id, Name='AfterPayAMI')
	 
time.sleep(30)

if len(amiImage['ImageId']) == 0:
        time.sleep(60)

logging.warning('Customized AMI image build for  AfterPay completed ... AMI image name is AfterPayAMI')


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
    DefaultCooldown=30,
    MaxSize=2,
    MinSize=2
)

response = client.attach_load_balancers(
    AutoScalingGroupName='AutoScaleGroup01',
    LoadBalancerNames=[
        'AWS-ELB-01',
    ]
)
