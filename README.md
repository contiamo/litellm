# Forked Litellm Repo

This litellm fork was made to extend the original functionalities by some additional callback functions that are expected to be present in the image builts.

## Additional Features

### Compliance Checker

### Introduction
When enabled via the litellm-config.yaml the compliance checker check wether or not a llm request violates compliance regulations and should be handled by a llm that is compliance approved.

In the current version, the intended llm request is initially forwarded to the compliant llm to have it checked for copliance conformity. 

a. If the request does not violate the regulations, it is simply being forwarded to the desired llm. 

b. If the request does violate the regulations, the intended request message(s) is being replaced by the request to simply return a statement that a compliance safe llm should be used. This way, no sensitive information finds it way to the unsafe llm.

#### What changed to the original repository?

One new file was created and one file was adjusted.

litellm/proxy/hooks/compliance_checker.py is the new file with the callback logic.

litellm/proxy/common_utils/callback_utils.py has some additional lines 221-227.

In these lines it was made sure that the new file and logic is being included into the litellm project.

#### How to enable the feature?

1) in the litellm-config.yaml add callbacks: ['complaince_checker'] like so:

```yaml
litellm_settings:
  callbacks: ["compliance_checker"]
```
2) add two new environment variables
COMPLIANCE_MODEL
COMPLIANCE_MODEL_URL

#### Current Limitations

- The first POC was designed to work with a llama3 model as compliance model that is being hosted with an openai api structure without an API key, but that needs a verified ip address. Thus, not any model can be used at the moment and adjustments would be necessary.
- The system prompt to validate the compliance conformity is not well thought through yet
