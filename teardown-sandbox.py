import boto3
import os

# Set the profile to sandbox
boto3.setup_default_session(profile_name='sandbox')

# Create an EC2 Client
client = boto3.client('ec2')

# Define the search filter
filter = [{'Name': 'tag-key', 'Values': ['Name']}, {'Name': 'tag-value', 'Values': ['Sandbox']}]

# Terminate all running instance with tag-key Name and tag-value Sandbox
instanceIds = []
ec2s = client.describe_instances(Filters=filter)
for ec2 in ec2s['Reservations']:
    for instance in ec2['Instances']:
        if instance['State']['Name'] == 'running':
            instanceId = instance['InstanceId']
            instanceIds.append(instanceId)
            client.terminate_instances(InstanceIds=[instanceId])

# Wait for the instances to change their state to terminated
if len(instanceIds) > 0:
    print('Waiting for instances to terminate')
    waiter = client.get_waiter('instance_terminated')
    waiter.wait(InstanceIds=instanceIds)
    print("done")

# Delete the sandbox key-pair
client.delete_key_pair(KeyName='sandbox')

# Delete the VPC and all associated network resources with tag-key Name and tag-value Sandbox

# Get the VPC Id
vpcs = client.describe_vpcs(Filters=filter)
for vpc in vpcs['Vpcs']:
    vpcId = vpc['VpcId']

    # Delete the Security Group
    sgs = client.describe_security_groups(Filters=filter)
    # sgId = sgs['SecurityGroups'][0]['GroupId']
    for sg in sgs['SecurityGroups']:
        client.delete_security_group(GroupId=sg['GroupId'])

    # Detach and delete the internet gateway
    igws = client.describe_internet_gateways(Filters=filter)
    for igw in igws['InternetGateways']:
        client.detach_internet_gateway(InternetGatewayId=igw['InternetGatewayId'], VpcId=vpcId)
        client.delete_internet_gateway(InternetGatewayId=igw['InternetGatewayId'])

    # Delete the subnet
    sns = client.describe_subnets(Filters=filter)
    for sn in sns['Subnets']:
        client.delete_subnet(SubnetId=sn['SubnetId'])

    # Delete the route table
    rts = client.describe_route_tables(Filters=filter)
    for rt in rts['RouteTables']:
        client.delete_route_table(RouteTableId=rt['RouteTableId'])

    # Delete the VPC
    client.delete_vpc(VpcId=vpcId)

# Delete the local key-pair
if os.path.isfile("sandbox.pem"):
    print("Deleting local file: sandbox.pem")
    os.remove("sandbox.pem")
