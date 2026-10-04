variable "aws_profile" {
  description = "AWS CLI profile (SSO) to deploy with."
  type        = string
  default     = "advocacy-dev"
}

variable "region" {
  description = "us-west-2 is the closest region with every proxy type (c6g/c7g/c9g, mac2, mac-m4); us-west-1 has no C9g and no Mac hosts."
  type        = string
  default     = "us-west-2"
}

variable "availability_zone" {
  description = <<-EOT
    Default AZ for every proxy. All five instance types are offered in us-west-2a, but Mac
    Dedicated Hosts are zonal and capacity-limited: when AllocateHosts fails with
    InsufficientHostCapacity (the error names an AZ that has some), set that proxy's
    availability_zone override instead.
  EOT
  type        = string
  default     = "us-west-2a"
}

variable "name_prefix" {
  type    = string
  default = "fleet-phone-proxy"
}

variable "enabled_proxies" {
  description = <<-EOT
    Which proxies to create, by key of var.proxies. Start with one Linux proxy to shake out the
    bugs (e.g. ["android-flagship"]), then enable the rest to run in parallel. Mac proxies
    allocate a Dedicated Host with a 24-hour minimum charge the moment they're enabled.
    The default is whatever is deployed, so a plain `terraform plan`/`apply` changes nothing
    (and can't destroy a proxy mid-run); keep it in step when enabling or removing one.
  EOT
  type        = list(string)
  default     = ["android-flagship", "android-mainstream", "iphone-older"] # pi5 removed 2026-10-03
}

variable "proxies" {
  description = "Every platform on the spectrum. bench_threads is the llama-bench -t sweep for that platform's core count."
  type = map(object({
    instance_type     = string
    os                = string # "linux" | "macos"
    mimics            = string
    phone_bw_gbs      = number # memory bandwidth of the device being mimicked, for the generation-speed correction
    bench_threads     = string
    extra_models      = optional(list(object({ repo = string, file = string })), [])
    availability_zone = optional(string) # overrides var.availability_zone
  }))
  default = {
    "pi5" = {
      instance_type = "c6g.2xlarge"
      os            = "linux"
      mimics        = "Raspberry Pi 5 (Cortex-A76; Graviton2's Neoverse N1 is its server sibling)"
      phone_bw_gbs  = 17.1
      bench_threads = "1,2,4"
    }
    "android-mainstream" = {
      instance_type = "c7g.2xlarge"
      os            = "linux"
      mimics        = "mainstream / older Android (Cortex-X1 class; Graviton3 Neoverse V1)"
      phone_bw_gbs  = 51.2
      bench_threads = "1,2,4,6,8"
    }
    "android-flagship" = {
      instance_type = "c9g.2xlarge"
      os            = "linux"
      mimics        = "2025-26 flagship Android (Snapdragon 8 Elite Gen 5 / Dimensity 9500) - lower bound; Graviton5 Neoverse V3 ~ Cortex-X4"
      phone_bw_gbs  = 84.8
      bench_threads = "1,2,4,6,8"
    }
    "iphone-flagship" = {
      instance_type = "mac-m4.metal"
      os            = "macos"
      mimics        = "iPhone 17 Pro / 18 Pro (A19 Pro / A20 Pro); M4 is the A18 generation"
      phone_bw_gbs  = 76.8
      bench_threads = "4"
      # 16.5 GB: no phone or 16 GiB proxy can hold it; a laptop-class reference point only.
      extra_models = [{ repo = "unsloth/Qwen3.8-27B-GGUF", file = "Qwen3.8-27B-UD-Q4_K_M.gguf" }]
    }
    "iphone-older" = {
      instance_type = "mac2.metal"
      os            = "macos"
      mimics        = "iPhone 12-era (A14); M1 is its sibling"
      phone_bw_gbs  = 34.1
      bench_threads = "4"
      # 2026-10-03: no mac2.metal host capacity in us-west-2a; AWS pointed at us-west-2c.
      availability_zone = "us-west-2c"
    }
  }
}

variable "llama_cpp_ref" {
  description = "llama.cpp tag every proxy builds (v0.5.0 = commit 7fe450e1, 2026-09-23; c13fcbf6 is the annotated tag object, not the commit)."
  type        = string
  default     = "v0.5.0"
}

variable "models" {
  description = <<-EOT
    Phase 1: identical models on every platform, smallest first, so a run that stops early
    still has complete small-model results. The full models.toml candidate set (same repos
    and files as the original M4/Pi tests) minus Qwen3.8-27B, which no phone or 16 GiB proxy
    can hold, plus two calibration models with published iPhone 17 Pro / M4 Max numbers
    (Qwen3.5-2B, Gemma-4-E2B). Many of these FAIL the task quality gates (models.toml has
    each verdict); speed and energy don't depend on quality, so they map size vs. speed.
  EOT
  type = list(object({
    repo = string
    file = string
  }))
  default = [
    { repo = "unsloth/granite-4.0-h-350m-GGUF", file = "granite-4.0-h-350m-Q8_0.gguf" },
    { repo = "NANI-Nithin/LFM2.5-350M-RLCD-GGUF", file = "LFM2.5-350M-RLCD-Q8_0.gguf" },
    { repo = "Qwen/Qwen2.5-0.5B-Instruct-GGUF", file = "qwen2.5-0.5b-instruct-q4_k_m.gguf" },
    { repo = "drmcbride/Qwen3-0.6B-Q8_0-GGUF", file = "qwen3-0.6b-q8_0.gguf" },
    { repo = "ggml-org/gemma-3-1b-it-GGUF", file = "gemma-3-1b-it-Q4_K_M.gguf" },
    { repo = "unsloth/Llama-3.2-1B-Instruct-GGUF", file = "Llama-3.2-1B-Instruct-Q4_K_M.gguf" },
    { repo = "Qwen/Qwen2.5-1.5B-Instruct-GGUF", file = "qwen2.5-1.5b-instruct-q4_k_m.gguf" },
    { repo = "unsloth/Qwen3.5-2B-GGUF", file = "Qwen3.5-2B-Q4_K_M.gguf" },
    { repo = "unsloth/Llama-3.2-3B-Instruct-GGUF", file = "Llama-3.2-3B-Instruct-Q4_K_M.gguf" },
    { repo = "Qwen/Qwen2.5-3B-Instruct-GGUF", file = "qwen2.5-3b-instruct-q4_k_m.gguf" },
    { repo = "bartowski/Phi-3.5-mini-instruct-GGUF", file = "Phi-3.5-mini-instruct-Q4_K_M.gguf" },
    { repo = "unsloth/gemma-3-4b-it-GGUF", file = "gemma-3-4b-it-Q4_K_M.gguf" },
    { repo = "unsloth/gemma-4-E2B-it-GGUF", file = "gemma-4-E2B-it-Q4_K_M.gguf" },
    { repo = "bloomer010/Ling-3.0-tiny-GGUF", file = "Ling-3.0-tiny-Q4_K_M.gguf" },
    { repo = "unsloth/Llama-3.1-8B-Instruct-GGUF", file = "Llama-3.1-8B-Instruct-Q4_K_M.gguf" },
    { repo = "Aldaris/Qwen3-8B-Q4_K_M-GGUF", file = "qwen3-8b-q4_k_m.gguf" },
    { repo = "unsloth/GLM-4-9B-0414-GGUF", file = "GLM-4-9B-0414-Q4_K_M.gguf" },
  ]
}

variable "linux_auto_stop_hours" {
  description = "Safety net: Linux proxies power themselves off (stop, not terminate; EBS and results survive) after this many hours."
  type        = number
  default     = 24
}

variable "macos_ami_name_prefix" {
  description = "macOS 26.x is mature and supports both M1 and M4; 27.0 shipped days ago."
  type        = string
  default     = "amzn-ec2-macos-26.7"
}

variable "ssh_allowed_cidr" {
  description = "CIDR allowed to SSH in. Empty = auto-detect this machine's public IP (/32)."
  type        = string
  default     = ""
}
