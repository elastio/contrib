variable "pipeline_name" {
  description = "A name to give to the pipeline"
  type        = string
  default     = "elastio-demo"
}

variable "region" {
  description = "The AWS region to operate upon"
  type        = string
  default     = "us-east-2"
}

variable "vpc_cidr_block" {
  description = "Used to select the VPC to use in your account"
  type        = string
  default     = "10.0.0.0/16"
}
