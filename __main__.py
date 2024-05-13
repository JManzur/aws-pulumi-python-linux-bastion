from pulumi import (
    Config,
    get_stack,
    StackReference,
    export
)
from objects import BastionInstanceProfile, BastionHost

# Instantiate the Pulumi configuration and load the environment variables:
config = Config()
common_tags = config.require_object("common_tags")

# Variables with default values:
name_prefix = config.get("name_prefix") or "k8s-bastion"
k8s_version = config.get("k8s_version") or "1.28.8"
instance_type = config.get("instance_type") or "t2.micro"
vpc_stack_name = config.get("vpc_stack_name") or "vpc"

# Load VPC values, from the VPC stack:
stack = get_stack()
vpc_stack_reference = StackReference(f"organization/{vpc_stack_name}/{stack}")
vpc_id = vpc_stack_reference.require_output("vpc_id")
private_subnets = vpc_stack_reference.require_output("private_subnets")
vpc_cidr_block = vpc_stack_reference.require_output("vpc_cidr")

# If you are not using the VPC stack reference, create the variables in the stack file and use the following code:
"""
vpc_id = config.require("vpc_id")
private_subnets = config.require("private_subnets")
vpc_cidr_block = config.require("vpc_cidr")
"""

# Create an instance profile for the bastion host
instance_profile = BastionInstanceProfile(
    "k8s-bastion-instance-profile",
    name_prefix=name_prefix,
    common_tags=common_tags
)
# Create the bastion host
bastion = BastionHost(
    "k8s-bastion-host",
    name_prefix=name_prefix,
    instance_profile_arn=instance_profile.arn,
    vpc_id=vpc_id,
    vpc_cidr=vpc_cidr_block,
    subnets=private_subnets,
    instance_type=instance_type,
    k8s_version=k8s_version,
    common_tags=common_tags
)

# Export the launch template ID and Auto Scaling Group name
export('launch_template_id', bastion.launch_template_id)
export('asg_name', bastion.asg_name)
