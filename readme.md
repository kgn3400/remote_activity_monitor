
<!-- markdownlint-disable MD041 -->
![GitHub all releases](https://img.shields.io/github/downloads/kgn3400/remote_activity_monitor/total)
![GitHub last commit](https://img.shields.io/github/last-commit/kgn3400/remote_activity_monitor)
![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/kgn3400/remote_activity_monitor)
[![Validate% with hassfest](https://github.com/kgn3400/remote_activity_monitor/workflows/Validate%20with%20hassfest/badge.svg)](https://github.com/kgn3400/remote_activity_monitor/actions/workflows/hassfest.yaml)

<img align="left" width="80" height="80" src="https://kgn3400.github.io/remote_activity_monitor/assets/icon.png" alt="App icon">

# Remote activity monitor

<br/>

The Remote Activity Monitor lets you keep track of the status of one or more binary or switch sensors on a remote Home Assistant device. This is especially useful if you want to monitor activity in another location—such as a separate home or a family member’s residence.
For example, I wanted to ensure the well-being of an elderly family member by receiving an alert if there was no activity detected for a certain period. A simple and cost-effective solution was to set up a Raspberry Pi with Home Assistant and a few motion sensors in their home.

Additionally, the integration [Remote Home-Assistant](https://github.com/custom-components/remote_homeassistant), a script, and an automation were needed to achieve the desired functionality.

This led to the creation of the custom integration, Remote Activity Monitor, which brings everything together in a single, user-friendly interface. Now, all the necessary features are bundled in one place, making setup and monitoring simple and straightforward for everyone.

## Installation

For installation search for Remote activity monitor in the HACS and download.
Or click
[![My Home Assistant](https://img.shields.io/badge/Home%20Assistant-%2341BDF5.svg?style=flat&logo=home-assistant&label=Add%20to%20HACS)](https://my.home-assistant.io/redirect/hacs_repository/?owner=kgn3400&repository=remote_activity_monitor&category=integration)

## Configuration

Configuration is done through the Home Assistant UI. To add a new entry, simply go to [Settings > Devices & Services](https://my.home-assistant.io/redirect/integrations) and click the add button. Next choose the [Remote activity monitor](https://my.home-assistant.io/redirect/config_flow_start?domain=remote_activity_monitor) option.

Or click
[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=remote_activity_monitor)

Select whether you want to create a “Remote Activity Monitor” or a “Main Activity Monitor” integration. Note that you must always set up a Remote Activity Monitor first before you can create a Main Activity Monitor. This sequence ensures proper communication between your monitoring devices.

<img src="https://kgn3400.github.io/remote_activity_monitor/assets/config-menu.png" width="400" height="auto" alt="Config">
<br>

On the remote Home Assistant instance, add the Remote Activity Monitor integration. Then, simply select the entities you want to monitor.

To access the remote Home Assistant, you need a Long-Lived Access Token. Generate a Long-Lived Access Token by logging into the remote Home Assistant, click on the [user profile icon](https://my.home-assistant.io/redirect/profile) and click on the security tab, then click "Create Token" under "Long-Lived Access Tokens". Copy the token and use it when creating the main activity monitor.

<img src="https://kgn3400.github.io/remote_activity_monitor/assets/config-remote.png" width="400" height="auto" alt="Config">
<br>

Enter the remote host name or ip address and insert the Long-Lived Access Token that was generated on the remote host.

<img src="https://kgn3400.github.io/remote_activity_monitor/assets/config-main-1.png" width="400" height="auto" alt="Config">
<br>

Select the Remote activity monitor entity that you want to monitor on the remote host. Should there be any delay before marking the state as changed and the state to monitor.

<img src="https://kgn3400.github.io/remote_activity_monitor/assets/config-main-2.png" width="400" height="auto" alt="Config">

### Support

If you like this integration or find it useful, please consider giving it a ⭐️ on GitHub 👍 Your support is greatly appreciated!
