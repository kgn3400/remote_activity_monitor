
<!-- markdownlint-disable MD041 -->
![GitHub all releases](https://img.shields.io/github/downloads/kgn3400/remote_activity_monitor/total)
![GitHub last commit](https://img.shields.io/github/last-commit/kgn3400/remote_activity_monitor)
![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/kgn3400/remote_activity_monitor)
[![Validate% with hassfest](https://github.com/kgn3400/remote_activity_monitor/workflows/Validate%20with%20hassfest/badge.svg)](https://github.com/kgn3400/remote_activity_monitor/actions/workflows/hassfest.yaml)

<img align="left" width="80" height="80" src="https://kgn3400.github.io/remote_activity_monitor/assets/icon.png" alt="App icon">

# Remote activity monitor

<br/>
The Remote activity monitor allows you to monitor the status of a binary/switch sensor or a set of binary/switch sensors on a remote Home Assistant device.

My use case was that I wanted to monitor an elderly family member and receive an alert if there had been no activity for a given period. A cheap and flexible solution was to install a Raspberry Pi with Home Assistant and some motion sensors.

Additionally, the integration [Remote Home-Assistant](https://github.com/custom-components/remote_homeassistant), a script, and an automation were needed to achieve the desired functionality.

Instead, it resulted in the custom integration Remote Activity Monitor, where everything is bundled into a user-friendly interface that is simple to use.

## Installation

For installation instructions, until the Remote activity monitor is part of HACS, [see this guide](https://hacs.xyz/docs/faq/custom_repositories).
Or click
[![My Home Assistant](https://img.shields.io/badge/Home%20Assistant-%2341BDF5.svg?style=flat&logo=home-assistant&label=Add%20to%20HACS)](https://my.home-assistant.io/redirect/hacs_repository/?owner=kgn3400&repository=remote_activity_monitor&category=integration)

## Configuration

Configuration is setup via UI in Home Assistant. To add one, go to [Settings > Devices & Services](https://my.home-assistant.io/redirect/integrations) and click the add button. Next choose the [Remote activity monitor](https://my.home-assistant.io/redirect/config_flow_start?domain=remote_activity_monitor) option.

Or click
[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=remote_activity_monitor)

Choose whether it is a remote activity monitor integration or a main activity monitor integration which should be created. A remote activity monitor must always be created before creating a main activity monitor.

<img src="https://kgn3400.github.io/remote_activity_monitor/assets/config-menu.png" width="400" height="auto" alt="Config">
<br>

On the remote Home Assistant, add the remote activity monitor integration. And select which entities to track.

To access the remote Home Assistant, you need a Long-Lived Access Token. Generate a Long-Lived Access Token by logging into the remote Home Assistant, click on the [user profile icon](https://my.home-assistant.io/redirect/profile) and click on the security tab, then click "Create Token" under "Long-Lived Access Tokens". Copy the token and use it when creating the main activity monitor.

<img src="https://kgn3400.github.io/remote_activity_monitor/assets/config-remote.png" width="400" height="auto" alt="Config">
<br>

Enter the remote host name or ip address and insert the Long-Lived Access Token that was generated on the remote host.

<img src="https://kgn3400.github.io/remote_activity_monitor/assets/config-main-1.png" width="400" height="auto" alt="Config">
<br>

Select the Remote activity monitor entity that you want to monitor on the remote host. Should there be any delay before marking the state as changed and the state to monitor.

<img src="https://kgn3400.github.io/remote_activity_monitor/assets/config-main-2.png" width="400" height="auto" alt="Config">
