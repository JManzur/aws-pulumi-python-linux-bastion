#!/bin/bash

# Global variables:
ARCH="amd64"
PLATFORM=$(uname -s)_$ARCH
K8S_VERSION=$1

# Update the system:
yum update -y

# Install cli tools:
yum install telnet -y
yum install jq -y
yum install tree -y
yum install nfs-utils -y
yum install git -y
yum install whois -y
yum install htop -y
yum install yum-utils -y

# Install oh-my-bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/ohmybash/oh-my-bash/master/tools/install.sh)" --unattended

# Install Docker:
yum install docker -y
service docker start
usermod -a -G docker ec2-user

# Install kubectl:
# Ref: https://docs.aws.amazon.com/eks/latest/userguide/install-kubectl.html
curl -O "https://s3.us-west-2.amazonaws.com/amazon-eks/$K8S_VERSION/2024-04-19/bin/linux/$ARCH/kubectl"
chmod +x ./kubectl
mkdir -p $HOME/bin && cp ./kubectl $HOME/bin/kubectl && export PATH=$HOME/bin:$PATH
echo 'alias k=kubectl' >> ~/.bashrc
echo 'export PATH=$HOME/bin:$PATH' >> ~/.bashrc
source <(kubectl completion bash)
echo "source <(kubectl completion bash)" >> ~/.bashrc

# Install eksctl:
curl -sLO "https://github.com/eksctl-io/eksctl/releases/latest/download/eksctl_$PLATFORM.tar.gz"
tar -xzf eksctl_$PLATFORM.tar.gz -C /tmp && rm eksctl_$PLATFORM.tar.gz
mv /tmp/eksctl /usr/local/bin

# Install the flux cli:
curl -s https://fluxcd.io/install.sh | sudo bash

# Install the kustomize cli:
curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh"  | bash
chmod a+x kustomize
mv kustomize /usr/local/bin/kustomize

# Install the helm cli:
curl -s "https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3" | bash