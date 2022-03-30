data "aws_iam_policy_document" "ec2_assume" {
  statement {
    sid     = "EC2InstanceTrustPolicy"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

data "aws_iam_policy" "elastio_access" {
  name = "ElastioFullAdmin"
}

data "aws_vpc" "default" {
  cidr_block = var.vpc_cidr_block
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"]
  }
}

resource "aws_iam_role" "elastio_instance" {
  name               = "EC2InstanceElastioAdmin"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

resource "aws_iam_role_policy_attachment" "elastio_instance" {
  role       = aws_iam_role.elastio_instance.name
  policy_arn = data.aws_iam_policy.elastio_access.arn
}

resource "aws_iam_instance_profile" "elastio_instance" {
  name = "EC2InstanceElastioAdmin"
  role = aws_iam_role.elastio_instance.name
}

data "template_cloudinit_config" "ec2_config" {
  gzip          = false
  base64_encode = true

  part {
    content_type = "text/x-shellscript"
    content      = <<EoF
#!/bin/bash
sudo /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/elastio/elastio-stack/master/scripts/install-elastio.sh) $0" -- -c
EoF
  }
}

resource "aws_security_group" "elastio_instance" {
  name        = "elastio-instance-sg"
  description = "Allow access into test instance for elastio"
  vpc_id      = data.aws_vpc.default.id

  egress {
    description = "Outbound access anywhere"
    from_port   = 0
    to_port     = 0
    protocol    = -1
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH access"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "test_instance" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = "t3a.medium"
  associate_public_ip_address = true
  iam_instance_profile        = aws_iam_instance_profile.elastio_instance.name
  vpc_security_group_ids      = [aws_security_group.elastio_instance.id]
  user_data_base64            = data.template_cloudinit_config.ec2_config.rendered
  subnet_id                   = data.aws_subnets.default.ids[0]
}
