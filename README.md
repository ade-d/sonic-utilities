[![Total alerts](https://img.shields.io/lgtm/alerts/g/Azure/sonic-utilities.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/Azure/sonic-utilities/alerts/)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/Azure/sonic-utilities.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/Azure/sonic-utilities/context:python)

[![Build](https://sonic-jenkins.westus2.cloudapp.azure.com/job/common/job/sonic-utilities-build/badge/icon)](https://sonic-jenkins.westus2.cloudapp.azure.com/job/common/job/sonic-utilities-build/)

# SONiC: Software for Open Networking in the Cloud

## sonic-utilities

Command-line utilities for SONiC

This repository produces two packages, as follows:

### sonic-utilities

A Python wheel package, containing all the Python source code for the command-line utilities

#### To build

```
python2 setup.py bdist_wheel
```

#### To run unit tests

```
python2 setup.py test
```


### sonic-utilities-data

A Debian package, containing data files needed by the utilities (bash_completion files, Jinja2 templates, etc.)

#### To build

Instructions for building the sonic-utilities-data package can be found in [sonic-utilities-data/README.md](https://github.com/Azure/sonic-utilities/blob/master/sonic-utilities-data/README.md)

---

## Contribution guide

All contributors must sign a contribution license agreement (CLA) before contributions can be accepted. This process is now automated via a GitHub bot when submitting new pull request. If the contributor has not yet signed a CLA, the bot will create a comment on the pull request containing a link to electronically sign the CLA.

### GitHub Workflow

We're following basic GitHub Flow. If you have no idea what we're talking about, check out [GitHub's official guide](https://guides.github.com/introduction/flow/). Note that merge is only performed by the repository maintainer.

Guide for performing commits:

* Isolate each commit to one component/bugfix/issue/feature
* Use a standard commit message format:

>     [component/folder touched]: Description intent of your changes
>
>     [List of changes]
>
> 	  Signed-off-by: Your Name your@email.com

For example:

>     swss-common: Stabilize the ConsumerTable
>
>     * Fixing autoreconf
>     * Fixing unit-tests by adding checkers and initialize the DB before start
>     * Adding the ability to select from multiple channels
>     * Health-Monitor - The idea of the patch is that if something went wrong with the notification channel,
>       we will have the option to know about it (Query the LLEN table length).
>
>       Signed-off-by: John Doe user@dev.null


* Each developer should fork this repository and [add the team as a Contributor](https://help.github.com/articles/adding-collaborators-to-a-personal-repository)
* Push your changes to your private fork and do "pull-request" to this repository
* Use a pull request to do code review
* Use issues to keep track of what is going on
