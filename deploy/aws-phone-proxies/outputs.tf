output "proxies" {
  description = "Everything scripts/proxyctl.sh needs, per enabled proxy."
  value = merge(
    {
      for k, i in aws_instance.linux : k => {
        ip            = i.public_ip
        user          = "ubuntu"
        base          = "/opt/phoneproxy"
        os            = "linux"
        instance_type = i.instance_type
        mimics        = var.proxies[k].mimics
        phone_bw_gbs  = var.proxies[k].phone_bw_gbs
        bench_threads = var.proxies[k].bench_threads
      }
    },
    {
      for k, i in aws_instance.mac : k => {
        ip            = i.public_ip
        user          = "ec2-user"
        base          = "/Users/ec2-user/phoneproxy"
        os            = "macos"
        instance_type = i.instance_type
        mimics        = var.proxies[k].mimics
        phone_bw_gbs  = var.proxies[k].phone_bw_gbs
        bench_threads = var.proxies[k].bench_threads
      }
    },
  )
}

output "ssh_key_path" {
  value = local_sensitive_file.ssh_private_key.filename
}

output "mac_hosts_earliest_release" {
  description = "AWS bills Mac Dedicated Hosts for at least 24 h and refuses to release them sooner."
  value = {
    for k, t in time_static.mac_host_allocated : k => {
      host_id          = aws_ec2_host.mac[k].id
      allocated_at     = t.rfc3339
      earliest_release = timeadd(t.rfc3339, "24h")
    }
  }
}
