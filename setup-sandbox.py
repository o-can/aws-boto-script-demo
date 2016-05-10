import boto3

# Set the profile to sandbox
boto3.setup_default_session(profile_name='sandbox')

# Create an EC2 Client
client = boto3.client('ec2')

# Create Sandbox key-pair
kp = client.create_key_pair(KeyName='sandbox')
pk = kp['KeyMaterial']
with open("sandbox.pem", "w") as text_file:
    text_file.write(pk)

# Describe AZs, Get first AZ Name
azs = client.describe_availability_zones()
zoneName = azs['AvailabilityZones'][0]['ZoneName']

# Create a Sandbox VPC
vpc = client.create_vpc(CidrBlock='192.168.0.0/16', InstanceTenancy='default')
client.modify_vpc_attribute(VpcId=vpc['Vpc']['VpcId'], EnableDnsSupport={'Value': True})
client.modify_vpc_attribute(VpcId=vpc['Vpc']['VpcId'], EnableDnsHostnames={'Value': True})

# Create a Subnet in the VPC
subnet = client.create_subnet(VpcId=vpc['Vpc']['VpcId'], CidrBlock='192.168.1.0/24', AvailabilityZone=zoneName)

# Modify Subnet: Set Map Public IP On Launch
client.modify_subnet_attribute(SubnetId=subnet['Subnet']['SubnetId'], MapPublicIpOnLaunch={'Value': True})

# Create an Internet Gateway
igw = client.create_internet_gateway()

# Attach Internet Gateway to Sandbox VPC
client.attach_internet_gateway(InternetGatewayId=igw['InternetGateway']['InternetGatewayId'], VpcId=vpc['Vpc']['VpcId'])

# Create Route Table
rt = client.create_route_table(VpcId=vpc['Vpc']['VpcId'])

# Create Route for Internet Gateway in Route Table
client.create_route(RouteTableId=rt['RouteTable']['RouteTableId'], DestinationCidrBlock='0.0.0.0/0',
                    GatewayId=igw['InternetGateway']['InternetGatewayId'])

# Associate Route Table with Subnet
client.associate_route_table(SubnetId=subnet['Subnet']['SubnetId'], RouteTableId=rt['RouteTable']['RouteTableId'])

# Create a Public SSH Ingress Security Group in VPC
sg = client.create_security_group(GroupName='Sandbox SSH', Description='Public SSH Ingress for Sandbox',
                                  VpcId=vpc['Vpc']['VpcId'])
# Authorize Ingress TCP Port 22 from CIDR 0.0.0.0/0
client.authorize_security_group_ingress(GroupId=sg['GroupId'], IpProtocol='tcp', FromPort=22, ToPort=22,
                                        CidrIp='0.0.0.0/0')

# Describe Images, Filter by description = Amazon Linux AMI 2016.03.1 x86_64 minimal HVM EBS
amis = client.describe_images(
    Filters=[{'Name': 'description', 'Values': ['Amazon Linux AMI 2016.03.1 x86_64 minimal HVM EBS']}])
# Get AMI Id of first result
amiId = amis['Images'][0]['ImageId']

# Launch one t2.small instance in the Subnet and assign the pre-generated Sandbox key
ec2 = client.run_instances(MinCount=1, MaxCount=1, ImageId=amiId, KeyName='sandbox', SecurityGroupIds=[sg['GroupId']],
                           InstanceType='t2.small',
                           SubnetId=subnet['Subnet']['SubnetId'])

# Tag all resources
client.create_tags(
    Resources=[vpc['Vpc']['VpcId'], ec2['Instances'][0]['InstanceId'], sg['GroupId'], rt['RouteTable']['RouteTableId'],
               subnet['Subnet']['SubnetId'], igw['InternetGateway']['InternetGatewayId']],
    Tags=[{'Key': 'Name', 'Value': 'Sandbox'}])

# Wait for the instance to change it's state to running
print('Waiting for instance with Id: ' + ec2['Instances'][0]['InstanceId'])
waiter = client.get_waiter('instance_running')
waiter.wait(InstanceIds=[ec2['Instances'][0]['InstanceId']])
print("done")

# Print out the public ip address
res = client.describe_instances(InstanceIds=[ec2['Instances'][0]['InstanceId']])
print("Public IP Address: " + res['Reservations'][0]['Instances'][0]['PublicIpAddress'])
