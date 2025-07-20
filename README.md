# restsession

![PyPI - Python Version](https://img.shields.io/pypi/pyversions/restsession)
[![CI](https://github.com/palmersample/restsession/actions/workflows/ci.yml/badge.svg)](https://github.com/palmersample/restsession/actions/workflows/ci.yml)
[![PyPi Release](https://github.com/palmersample/restsession/actions/workflows/release.yml/badge.svg)](https://github.com/palmersample/restsession/actions/workflows/release.yml) 
![PyPI - Version](https://img.shields.io/pypi/v/restsession)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI Downloads](https://static.pepy.tech/badge/restsession)](https://pepy.tech/projects/restsession)
[![Pydantic v2](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/pydantic/pydantic/main/docs/badge/v2.json)](https://pydantic.dev)




HTTP Session package for RESTful API consumption. This project is a wrapper for the Python "requests" library that incorporates features that normally must be added for each project such a automatic Retry support, Base URL sessions, and non-standard authorization header removal on cross-domain redirects. Configuration for each feature is performed by modifying object attributes for the RestSession instance.

Two classes are provided for use: **RestSession** and **RestSessionSingleton**.

**RestSession** is the class that you will likely use most often, and instantiation is identical to the `requests_toolbelt.sessions.BaseURLSession` class.

You might find the **RestSessionSingleton** class useful if you have modules in a larger project that must make REST API requests to an endpoint using common attributes, such as authentication. Instantiating and configuring a RestSessionSingleton instance in your project allows you to access the single instance, in any module, and perform requests without re-defining the same attributes.  

This project exists because I frequently create projects that use `requests` in the same manner, and I got tired of repeating myself :smiley:

# Installation

This project has been uploaded to PyPi. To install, use the Python `pip` command:

`pip install restsession`

# Usage

Instances can be created explicitly or using a context manager. All methods from the requests library should be available for use.

Explicit implementation example:

```python
from restsession import RestSession

session = RestSession()
result = session.get("https://example.local/path/to/resource")

if result.ok:
    # Do something on success
```

Or, for a Singleton session:

```python
from restsession import RestSessionSingleton

session = RestSessionSingleton()
result = session.get("https://example.local/path/to/resource")

if result.ok:
    # Do something on success
```

**Base URL Session**

For projects intended to interact with a single endpoint (for example, RESTCONF on a single network device), Base URL sessions are supported. Base URL sessions allow you to instantiate the class with a common path, and all subsequent requests are made to a path relative to the Base URL. Example:

```python
# Example RESTCONF usage

from restsession import RestSession

session = RestSession(base_url="https://network.device/restconf/data/Cisco-IOS-XE-native:native/")
session.auth = ("username", "password")
session.headers.update({"Content-Type": "application/yang-data+json",
                        "Accept": "application/yang-data+json"})

result = session.get("interface/GigabitEthernet=1")

print(result.json())
```

**Note the trailing slash (`/`) on the Base URL and the lack of leading slash in the target URL!** This is due to the behavior of `urllib.parse.urljoin`, used to generate the final URL. This behavior can be overridden using the `always_relative_url` option (see Attributes, below).

# Attributes and Defaults

## Request behaviors (commonly modified):

All attributes are OPTIONAL. Defaults are set, but can be overridden by modifying the attribute value.

**base_url** (string): Any valid URL to be used as the base URL for subsequent requests. URLs specified for individual requests should be supplied relative to the base URL, when defined. *Default: None*

**always_relative_url** (bool): Override the `urllib.parse.urljoin` default behavior and assume that any path is relative to the base URL, if one has been defined. This is to reduce headaches which occur from trying to figure out why a path isn't being retrieved because of a missing trailing slash / present leading slash. *Default: True* 

**auth** (tuple | requests.auth.AuthBase): If provided as a tuple(username, password), specify Basic Authorization for the session. Alternately accepts a custom auth class of type `requests.auth.AuthBase`. *Default: None* 

**remove_headers_on_redirect** (list): List of custom auth headers to be removed on cross-domain redirect. *Default: None*

**backoff_factor** (float): Exponential backoff factor for retries when a Retry-After header was not returned by the server. *Default: 0.3* 

**headers** (dict): Headers to include with the request. **Note**: use `headers.update()` to leave existing headers intact; explicitly setting headers will override any previously defined or default headers. *Default: Content-Type and Accept set to application/json. User-Agent and Keepalive are set.*

**max_reauth** (int): Maximum number of times to attempt to reauthenticate and retry an unauthorized request before an Exception is raised. *Default: 3*

**max_redirects** (int): Maximum number of redirects to follow before an Exception is raised. *Default: 16*

**respect_retry_headers** (bool): If a Retry-After header is sent by the server, whether to honor the value. If False, immediately retry the request. *Default: True*

**retries** (int): Maximum number of retries to perform before an Exception is raised. *Default: 3*

**timeout** (float | tuple\[float,float\]): Request timeout, in seconds. If provided as a tuple, the first value is the connection timeout and the second value is the read timeout (amount of time to wait for data to be returned by the server). A single value uses the same timeout for connect and read. *Default: 3*

**verify** (bool): Whether to perform TLS certificate chain validation. **Security risk! Only set to False for development purposes, or if you know the risks of disabling TLS validation!** *Default: True*

## Additional attributes (most users can ignore these):

**request_exception_hook** (Callable): Callable to handle (and raise) exceptions when request errors are encountered. *Default: see "Exceptions", below.*

**response_hooks** (Callable): *\[Advanced usage\]* Callable to be invoked after a response is received from the server. *Default: None*

**retry_method_list** (list\[str\]): List of HTTP methods for which retries should be attempted when a status matching *retry_status_code_list* is received. *Default: HEAD, GET, PUT, POST, PATCH, DELETE, OPTIONS, TRACE*

**retry_status_code_list** (list\[int\]): List of HTTP status codes that will trigger an automatic retry of the request. *Default: 408 (Request timeout), 413 (Payload too large), 429 (Too many requests), 503 (Service unavailable)*

**safe_arguments** (current unused) (bool): If an invalid value is supplied for an attribute, ignore and use the last good value instead of raising an Exception. *Default: True*

# Exceptions

## Project specific:

The following project-specific exceptions have been defined and can be imported to your code from the restsession.exceptions module:

**RestSessionError** is the base exception class from which other exceptions are derived.

**InvalidParameterError** will be raised if an invalid value or data type is provided for an attribute.

**InitializationError** will be raised on initial class instantiation if there is a error validating supplied parameters. Currently, the only parameter accepted is `base_url`, so verify that a valid URL has been supplied if this exception is raised.

## Request exceptions:

By default, exceptions raised by the `requests` library will be caught and re-raised. See the [requests.exceptions documentation](https://requests.readthedocs.io/en/latest/_modules/requests/exceptions/) for more information. 
