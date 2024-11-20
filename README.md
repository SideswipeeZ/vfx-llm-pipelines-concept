
# LLM in VFX - Concept

This is a proof of Concept pipeline intergration that aims to introcduce some LLM automated features to a new or existing pipeline by introducing some 'organic' elemnts to be able to extract data from a users message to feed that into a exisitng tool.

This is still a Demo/Work in Progress and should not be used with sensitive data.



## Demo

Here is a Demo Video.

https://youtu.be/9kkvIWOpwK8
[![Watch the video](https://img.youtube.com/vi/9kkvIWOpwK8/maxresdefault.jpg)](https://youtu.be/9kkvIWOpwK8)


## Overview

The LLM decides if the users message is relevant to either File Ingestion or Workspace setup. 

If it decides that it is relevant to the pipeline, it will try to process the message and then try to see what type of request from the user to parse and process from the list below.

If however it does not find a relevant message for pipeline, it will forward the message to the LLM provider and then return its message like it normally would if you interfaced with it.


### Abilities
There are Two main items that the demo provides:

* File Ingestion

* Workspace setup.

* LLM Forwarding

## Services Required
This example uses the following programs/services to function:
* [Docker](https://www.docker.com/ 'Docker')
* [OpenWebUI](https://openwebui.com/ 'OpenWebUI')
    - [OpenWebUI Pipeline](https://github.com/open-webui/pipelines 'OpenWebUI Pipeline')
* [Ollama](https://ollama.com/library 'Ollama')
* FAST API
* Python 3

## LLM Models
For the developemnet of this demo, the following models were used:
(All Models pulled from [Ollama](https://ollama.com/library 'Ollama') )
* [llama3.2:8B](https://ollama.com/library/llama3.2 'llama3.2:8B') 
* [llama3.1:70B](https://ollama.com/library/llama3.1 'llama3.1:70B') 
* [qwen2.5-coder:32B](https://ollama.com/library/qwen2.5-coder 'qwen2.5-coder:32B') 

All the above models should give a consise result.

## License

[MIT](https://choosealicense.com/licenses/mit/)

