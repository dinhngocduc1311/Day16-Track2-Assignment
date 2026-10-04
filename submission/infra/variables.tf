variable "aws_region" {
  description = "AWS Region"
  type        = string
  default     = "us-east-1"
}

variable "allowed_cidr" {
  description = "Public IPv4 /32 allowed to reach the Bastion and public ALB"
  type        = string

  validation {
    condition     = can(cidrnetmask(var.allowed_cidr)) && try(tonumber(split("/", var.allowed_cidr)[1]) == 32, false)
    error_message = "allowed_cidr must be one public IPv4 host in /32 form, for example 203.0.113.10/32."
  }
}

variable "enable_gpu" {
  description = "Set to true to deploy the optional GPU + vLLM LLM inference node instead of the default CPU + LightGBM node"
  type        = bool
  default     = false
}

variable "cpu_instance_type" {
  description = "Instance type for the default CPU (LightGBM) compute node"
  type        = string
  default     = "t3.medium"
}

variable "gpu_instance_type" {
  description = "Instance type for the optional GPU (vLLM) compute node"
  type        = string
  default     = "g6.xlarge"
}
