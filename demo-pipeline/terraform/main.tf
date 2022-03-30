terraform {}

provider "aws" {
  region = "us-east-2"
}

data "aws_region" "current" {}
