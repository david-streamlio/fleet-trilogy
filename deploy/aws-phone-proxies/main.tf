# Phone/edge-proxy benchmark fleet for Talk 2's "democratize edge intelligence" spectrum.
# See README.md for the platform mapping, costs (Mac hosts: 24-hour minimum) and run order.

provider "aws" {
  region  = var.region
  profile = var.aws_profile

  default_tags {
    tags = {
      Project   = "fleet-trilogy"
      Purpose   = "talk2-phone-proxy-benchmarks"
      ManagedBy = "terraform"
    }
  }
}

locals {
  enabled = { for k, v in var.proxies : k => v if contains(var.enabled_proxies, k) }
  linux   = { for k, v in local.enabled : k => v if v.os == "linux" }
  macos   = { for k, v in local.enabled : k => v if v.os == "macos" }

  # Each proxy's AZ, and a subnet for every AZ in use beyond the default one.
  az        = { for k, v in local.enabled : k => coalesce(v.availability_zone, var.availability_zone) }
  extra_azs = setsubtract(toset(values(local.az)), [var.availability_zone])
  subnet_id = { for k, az in local.az : k => az == var.availability_zone ? aws_subnet.public.id : aws_subnet.extra[az].id }

  ssh_cidr = var.ssh_allowed_cidr != "" ? var.ssh_allowed_cidr : "${chomp(data.http.my_ip[0].response_body)}/32"
  # Per proxy: the shared Phase 1 list plus that proxy's extra_models.
  models_list = { for k, v in var.proxies : k => join("\n", [for m in concat(var.models, v.extra_models) : "${m.repo} ${m.file}"]) }
}

data "http" "my_ip" {
  count = var.ssh_allowed_cidr == "" ? 1 : 0
  url   = "https://checkip.amazonaws.com"
}

# --- network: one small public subnet, SSH from this machine only -------------------------

resource "aws_vpc" "this" {
  cidr_block           = "10.42.0.0/16"
  enable_dns_hostnames = true
  tags                 = { Name = var.name_prefix }
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
  tags   = { Name = var.name_prefix }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.this.id
  cidr_block              = "10.42.1.0/24"
  availability_zone       = var.availability_zone
  map_public_ip_on_launch = true
  tags                    = { Name = "${var.name_prefix}-public" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }
  tags = { Name = "${var.name_prefix}-public" }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# Proxies placed outside the default AZ (Mac host capacity). 10.42.<10 + AZ letter index>.0/24.
resource "aws_subnet" "extra" {
  for_each = local.extra_azs

  vpc_id                  = aws_vpc.this.id
  cidr_block              = cidrsubnet(aws_vpc.this.cidr_block, 8, 10 + index(["a", "b", "c", "d", "e", "f"], substr(each.key, -1, 1)))
  availability_zone       = each.key
  map_public_ip_on_launch = true
  tags                    = { Name = "${var.name_prefix}-public-${each.key}" }
}

resource "aws_route_table_association" "extra" {
  for_each = local.extra_azs

  subnet_id      = aws_subnet.extra[each.key].id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "ssh" {
  name        = "${var.name_prefix}-ssh"
  description = "SSH from the operator IP only" # EC2 rejects apostrophes in SG descriptions
  vpc_id      = aws_vpc.this.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [local.ssh_cidr]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# --- SSH key: dedicated to this stack, so ~/.ssh is never touched ---------------------------

resource "tls_private_key" "ssh" {
  algorithm = "ED25519"
}

resource "local_sensitive_file" "ssh_private_key" {
  content         = tls_private_key.ssh.private_key_openssh
  filename        = "${path.module}/.ssh/${var.name_prefix}-ed25519"
  file_permission = "0600"
}

resource "aws_key_pair" "this" {
  key_name   = var.name_prefix
  public_key = tls_private_key.ssh.public_key_openssh
}

# --- Linux proxies (Graviton): Ubuntu 26.04 arm64 (GCC new enough for Neoverse V3) ---------

data "aws_ssm_parameter" "ubuntu_arm64" {
  name = "/aws/service/canonical/ubuntu/server/26.04/stable/current/arm64/hvm/ebs-gp3/ami-id"
}

resource "aws_instance" "linux" {
  for_each = local.linux

  ami                                  = data.aws_ssm_parameter.ubuntu_arm64.value
  instance_type                        = each.value.instance_type
  subnet_id                            = local.subnet_id[each.key]
  vpc_security_group_ids               = [aws_security_group.ssh.id]
  key_name                             = aws_key_pair.this.key_name
  instance_initiated_shutdown_behavior = "stop"

  user_data = templatefile("${path.module}/templates/linux_user_data.sh.tftpl", {
    llama_cpp_ref   = var.llama_cpp_ref
    models_list     = local.models_list[each.key]
    auto_stop_hours = var.linux_auto_stop_hours
  })
  user_data_replace_on_change = true

  root_block_device {
    volume_size = 80
    volume_type = "gp3"
  }

  metadata_options {
    http_tokens = "required"
  }

  # A newer "current" Ubuntu AMI must not replace a proxy mid-run (and wipe its results)
  # the next time any other proxy is applied.
  lifecycle {
    ignore_changes = [ami]
  }

  tags = { Name = "${var.name_prefix}-${each.key}", Mimics = each.value.mimics }
}

# --- macOS proxies: one Dedicated Host per instance (24-hour minimum allocation) -----------

data "aws_ami" "macos" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["${var.macos_ami_name_prefix}*"]
  }
  filter {
    name   = "architecture"
    values = ["arm64_mac"]
  }
}

resource "aws_ec2_host" "mac" {
  for_each = local.macos

  instance_type     = each.value.instance_type
  availability_zone = local.az[each.key]
  auto_placement    = "off"
  host_recovery     = "off"

  tags = { Name = "${var.name_prefix}-${each.key}-host" }
}

# When each host was allocated: AWS won't release a Mac host until 24 h after this.
resource "time_static" "mac_host_allocated" {
  for_each = local.macos
  triggers = { host_id = aws_ec2_host.mac[each.key].id }
}

resource "aws_instance" "mac" {
  for_each = local.macos

  ami                    = data.aws_ami.macos.id
  instance_type          = each.value.instance_type
  host_id                = aws_ec2_host.mac[each.key].id
  tenancy                = "host"
  subnet_id              = local.subnet_id[each.key]
  vpc_security_group_ids = [aws_security_group.ssh.id]
  key_name               = aws_key_pair.this.key_name

  user_data = templatefile("${path.module}/templates/macos_user_data.sh.tftpl", {
    llama_cpp_ref = var.llama_cpp_ref
    models_list   = local.models_list[each.key]
  })
  user_data_replace_on_change = true

  root_block_device {
    volume_size = 200
    volume_type = "gp3"
  }

  metadata_options {
    http_tokens = "required"
  }

  lifecycle {
    ignore_changes = [ami]
  }

  tags = { Name = "${var.name_prefix}-${each.key}", Mimics = each.value.mimics }
}
