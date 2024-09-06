# Remote Wrapper

This is an extensible Mythic Wrapper that allows payload wrapping to occur fully on a remote host. It uses Azure Service Bus for communication between Mythic and the remote host. Making it significantly easier to wrap payloads that require host or software spesific dependencies.


## How to install an agent in this format within Mythic

With the `mythic-cli` binary you can install this wrapper in one of three ways:

* `sudo ./mythic-cli install github https://github.com/Flangvik/remote_wrapper` to install the main branch
* `sudo ./mythic-cli install github https://github.com/Flangvik/remote_wrapper branchname` to install a specific branch of that repo
* `sudo ./mythic-cli install folder /path/to/local/folder/cloned/from/github` to install from an already cloned down version of an agent repo

## Credits
This repo used the [service_wrapper](https://github.com/its-a-feature/service_wrapper) by its-a-feature as a base.
