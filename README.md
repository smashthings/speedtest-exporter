# Speedtest Exporter

This is a prometheus exporter for speedtest results consisting of three endpoints, a html page at / telling you to go to /metrics, /metrics for prometheus based output, /json for a json dump of the speedtest results as prometheus output is ugly.

This is a fresh write using the speedtest python library by @sivel => https://github.com/sivel/speedtest-cli

Intended to be run as a docker container for both ARMv7 and AMD64 linux, images are at smasherofallthings/speedtest-exporter:<tag>

## Docker Compose Example

```
version: '2.1'
services:
  speedtest:
    container_name: speedtest
    image: "smasherofallthings/speedtest_exporter:armv7-latest"
    restart: unless-stopped
    network_mode: host # Change this as you like
```


