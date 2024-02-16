# restsession
HTTP Session package for RESTful API consumption

## Resolved: `requests` has limited retry support.
 
The base `requests` library will perform retries in some circumstances, but testing indicates that the retries will only be attempted if a `Retry-After` header is present in the response. Adding the

## Resolved: Non-standard Authorization headers not removed on cross-domain redirect

