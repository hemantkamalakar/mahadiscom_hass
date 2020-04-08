# A Home assistant custom component to get your MahaDiscom Energy Bill information.

To get started put all the files from`/custom_components/covid19indiatracker/` here:
`<config directory>/custom_components/covid19indiatracker/`

**Example configuration.yaml:**

```yaml
sensor:
  - platform: mahadiscom_hass
    ConsumerNo: 123123 
    BuNumber: 1234
    consumerType: 2
    scan_interval: 86400
```
