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

time.sleep(120)

amiImage = boto3.client('ec2').create_image(InstanceId=ec2InstanceAmi[0].instance_id, Name='AfterPayAMI')
	 

if len(amiImage['ImageId']) == 0:
        time.sleep(60)

time.sleep(120)


logging.warning('Customized AMI image build for  AfterPay completed ... AMI image name is AfterPayAMI')




######## Creating Security Groups ##########

securityGroupClient = boto3.client('ec2')

sgResponseA = securityGroupClient.describe_vpcs()
vpcId = sgResponseA.get('Vpcs', [{}])[0].get('VpcId', '')

sgresponseB = securityGroupClient.create_security_group(GroupName='ALLOW_SSH_HTTP',
                                         Description='Allow ssh traffic and web',
                                         VpcId=vpcId)
securityGroupId = sgresponseB['GroupId']
logging.warning('Security Group Created %s in vpc %s.', securityGroupId, vpcId)

data = securityGroupClient.authorize_security_group_ingress(
        GroupId=securityGroupId,
        IpPermissions=[
            {'IpProtocol': 'tcp',
             'FromPort': 80,
             'ToPort': 80,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'tcp',
             'FromPort': 22,
             'ToPort': 22,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
        ])


######### Creating Intermediate Server, installing Flask Development Server, download AfterPay app from Git and run ########

userDataScript= """#!/bin/bash
mkdir myproject
cd myproject
python3 -m venv venv
. venv/bin/activate
sudo pip install Flask
wget https://raw.githubusercontent.com/AfterpayTouch/recruitment-challenge-1/master/tiny_app.py
export FLASK_APP=tiny_app.py
sed -i "s/app.run()/app.run(host='0.0.0.0', debug=True, port=80)/g" tiny_app.py
sudo python tiny_app.py"""

ec2ServerResource = boto3.resource('ec2')
ec2Server = ec2ServerResource.create_instances(ImageId=amiImage['ImageId'],
                                            InstanceType='t2.micro',
                                            KeyName='AfterPaySSHKey',
                                            MinCount=1,
                                            MaxCount=1,
					     SecurityGroupIds=[
            					securityGroupId,
            				    ],
					    UserData=userDataScript)


checkStatusClient = boto3.client('ec2')
ec2ServerStatus = checkStatusClient.describe_instance_status(InstanceIds=[
                                   ec2Server[0].instance_id,
                                ])

while len(ec2ServerStatus['InstanceStatuses']) == 0:
        ec2ServerStatus = checkStatusClient.describe_instance_status(InstanceIds=[
                                   ec2Server[0].instance_id,
                                ])



time.sleep(120)

logging.warning('Installing Flask Development Server,Download AfterPay app from Git and run server on port 80')

######### Create an AutoScale Group with a Elastic Load Balancer ######


creatElbClient = boto3.client('elb')
elbResponse = creatElbClient.create_load_balancer(
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
        securityGroupId,
    ],
    Subnets=[
        ec2Server[0].subnet_id,
    ],
)



autoScaleClient = boto3.client('autoscaling')

creatASResponse = autoScaleClient.create_auto_scaling_group(
    AutoScalingGroupName='AutoScaleGroup01',
    InstanceId=ec2Server[0].instance_id,
    DesiredCapacity=2,
    DefaultCooldown=30,
    MaxSize=2,
    MinSize=2
)

attachElbResponse = autoScaleClient.attach_load_balancers(
    AutoScalingGroupName='AutoScaleGroup01',
    LoadBalancerNames=[
        'AWS-ELB-01',
    ]
)



######## Cleaning up intermediate EC2 instances #########


logging.warning('Hang on tight mate, It is almost there !')

time.sleep(300)

logging.warning('Please use Elastic Load Balancer DNS name to access AfterPay application : %s', elbResponse['DNSName'])

logging.warning('cleaning up enviroment ....')

time.sleep(10)

cleanUpEc2Client = boto3.client('ec2')
cleanUpEc2Response = cleanUpEc2Client.terminate_instances(
    InstanceIds=[
        ec2Server[0].instance_id,
    ]
)

cleanUpEc2Client = boto3.client('ec2')
cleanUpEc2Response = cleanUpEc2Client.terminate_instances(
    InstanceIds=[
        ec2InstanceAmi[0].instance_id,
    ]
)

logging.warning('AFterPay @ AWS Ready !')
