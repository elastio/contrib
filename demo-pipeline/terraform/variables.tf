variable "pipeline_name" {
  description = "A name to give to the pipeline"
  type        = string
}

variable "region" {
  description = "The AWS region to operate upon"
  type        = string
}

variable "vpc_cidr_block" {
  description = "Used to select the VPC to use in your account"
  type        = string
}
