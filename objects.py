from pulumi_aws.iam import (
    Role,
    RolePolicyAttachment,
    InstanceProfile,
)
from pulumi_aws.ec2 import (
    SecurityGroup,
    SecurityGroupIngressArgs,
    SecurityGroupEgressArgs,
    LaunchTemplate,
    get_ami,
)
from pulumi_aws.autoscaling import Group
from pulumi import ResourceOptions, ComponentResource
import json, base64


class BastionInstanceProfile(ComponentResource):
    def __init__(
            self,
            name: str,
            name_prefix: str,
            common_tags: dict,
            opts: ResourceOptions = None
        ):
        super().__init__("bastion:profile", name, {}, opts)
        self.name_prefix = name_prefix
        self.common_tags = common_tags

        role = Role(
            f"{name_prefix}-instance-profile-role",
            name=f"{name_prefix}-instance-profile-role",
            assume_role_policy=json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Action": "sts:AssumeRole",
                    "Effect": "Allow",
                    "Principal": {"Service": "ec2.amazonaws.com"},
                }]
            }),
            tags=common_tags
        )

        policy = RolePolicyAttachment(
            f"{name_prefix}-role-policy-attachment",
            role=role.name,
            policy_arn="arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
        )

        instance_profile = InstanceProfile(
            f"{name_prefix}-instance-profile-role",
            name=f"{name_prefix}-instance-profile-role",
            role=role.name,
            tags=common_tags
        )

        
        self.arn = instance_profile.arn
        """`pulumi.Output`: The ARN of the instance profile."""
        self.register_outputs({
            "arn": self.arn,
        })


class BastionHost(ComponentResource):
    def __init__(
            self,
            name: str,
            name_prefix: str,
            instance_profile_arn: str,
            vpc_id: str,
            vpc_cidr: str,
            subnets: list,
            instance_type: str,
            k8s_version: str,
            common_tags: dict,
            opts: ResourceOptions = None
        ):
        super().__init__("k8s-bastion:host", name, {}, opts)
        self.name_prefix = name_prefix
        self.instance_profile_arn = instance_profile_arn
        self.vpc_id = vpc_id
        self.vpc_cidr = vpc_cidr
        self.subnets = subnets
        self.instance_type = instance_type
        self.k8s_version = k8s_version
        self.common_tags = common_tags

        security_group = SecurityGroup(
            f"{name_prefix}-security-group",
            vpc_id=vpc_id,
            description="Allow all inbound traffic from VPC CIDR and all outbound traffic to the internet",
            ingress=[
                SecurityGroupIngressArgs(
                    from_port=0,
                    to_port=0,
                    protocol="-1",
                    cidr_blocks=[vpc_cidr],
                    description="Allow all inbound traffic from VPC CIDR",
                ),
            ],
            egress=[
                SecurityGroupEgressArgs(
                    from_port=0,
                    to_port=0,
                    protocol="-1",
                    cidr_blocks=["0.0.0.0/0"],
                    description="Allow all outbound traffic to the internet",
                ),
            ],
            tags=common_tags,
        )

        # Read the user data script from a file and encode it as base64 string.
        with open('./scripts/user_data.sh', 'r') as user_data_file:
            script_content = user_data_file.read()
            modified_content = script_content.replace(
                'K8S_VERSION=$1', 'K8S_VERSION="{}"'.format(k8s_version))
        user_data = base64.b64encode(
            modified_content.encode('utf-8')).decode('utf-8')

        amazon_linux_2023_ami = get_ami(
            filters=[
                {"name": "name", "values": ["al2023-ami-2023*-x86_64"]},
                {"name": "state", "values": ["available"]},
            ],
            owners=["amazon"],
            most_recent=True
        )

        launch_template = LaunchTemplate(
            f"{name_prefix}-launch-template",
            name_prefix=name_prefix,
            image_id=amazon_linux_2023_ami.id,
            vpc_security_group_ids=[security_group.id],
            instance_type=instance_type,
            user_data=user_data,
            iam_instance_profile={
                'arn': instance_profile_arn,
            },
            tags=common_tags
        )

        asg = Group(
            f"{name_prefix}-asg",
            name=name_prefix + '-asg',
            vpc_zone_identifiers=subnets,
            health_check_type='EC2',
            desired_capacity=1,
            max_size=2,
            min_size=1,
            launch_template={
                'id': launch_template.id,
                'version': "$Latest",
            },
            tags=[
                {
                    'key': 'Name',
                    'value': name_prefix + '-host',
                    'propagate_at_launch': True,
                },
                {
                    'key': 'Environment',
                    'value': common_tags['Environment'],
                    'propagate_at_launch': True,
                },
                {
                    'key': 'Owner',
                    'value': common_tags['Owner'],
                    'propagate_at_launch': True,
                },
                {
                    'key': 'ManagedBy',
                    'value': common_tags['ManagedBy'],
                    'propagate_at_launch': True,
                }
            ],
            instance_refresh={
                'strategy': 'Rolling',
                'preferences': {
                    'min_healthy_percentage': 100,
                },
                'triggers': ['tag'],
            }
        )

        self.launch_template_id = launch_template.id
        """`pulumi.Output`: The ID of the launch template."""
        self.asg_name = asg.name
        """`pulumi.Output`: The name of the Auto Scaling Group."""
        self.register_outputs({
            "launch_template_id": self.launch_template_id,
            "asg_name": self.asg_name,
        })
