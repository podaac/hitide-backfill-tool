variable "default_tags" {
  type = map(string)
  default = {}
}

variable "stage" {
  type = string
}

variable "region" {
  type = string
}

variable "cumulus_prefix" {
  type = string
}

variable "system_prefix" {
  type = string
  default = null
}

variable "system_bucket" {
  type = string
  default = null
}