import os
import json
import logging
from typing import List, Union, Generator, Iterator, final

from pydantic import BaseModel
import ollama
import requests
import httpx

logging.basicConfig(level=logging.DEBUG)


class Pipeline:
    class Valves(BaseModel):
        FLASK_HOST: str
        OLLAMA_HOST: str
        OLLAMA_MODEL: str
        EXTRA: str

    def __init__(self):
        self.name = "VFX Pipeline Helper DEV"
        self.flask_status = None
        self.ollama_client = None
        self.ollama_status = None

        self.valves = self.Valves(
            **{
                "pipelines": ["*"],
                "FLASK_HOST": os.getenv("FLASK_HOST", "http://localhost:5000"),
                "OLLAMA_HOST": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
                "OLLAMA_MODEL": os.getenv("OLLAMA_MODEL", "llama3.2"),
                "EXTRA": os.getenv("EXTRA", "")
            }
        )

    async def on_startup(self):
        # This function is called when the server is started.
        print(f"on_startup:{__name__}")
        self.heartbeat()

    async def on_shutdown(self):
        # This function is called when the server is shutdown.
        logging.info(f"on_shutdown:{__name__}")
        pass

    def heartbeat(self):
        #  Check if Flask Server is Running
        try:
            url = f'{self.valves.FLASK_HOST}/ping'

            response = requests.get(url)

            if response.status_code == 200:
                logging.info("Server is responding correctly:", response.json())
                self.flask_status = True
            else:
                logging.error("Failed to ping server:", response.text, "Status code:", response.status_code)
                self.flask_status = False
        except Exception as e:
            logging.error("An error occurred while testing the Flask server:", str(e))
            self.flask_status = False
        logging.info(f"Flask Status: {self.flask_status}")

        # Check if Ollama is running.
        self.ollama_client = ollama.Client(host=str(self.valves.OLLAMA_HOST))
        try:
            self.ollama_client.list()
            self.ollama_status = True
        except (httpx.ConnectError, ConnectionResetError) as e:
            logging.error(f"Connection error: {e}")
            self.ollama_status = False
        logging.info(f"Ollama Status: {self.ollama_status}")

    def connect_ollama(self, message, **kwargs):
        # This Function communicates with remote Ollama Host via message.
        ollama_model = self.valves.OLLAMA_MODEL
        if kwargs.get("model"):
            ollama_model = kwargs.get("model")

        ollama_result = self.ollama_client.chat(model=ollama_model, messages=[
                    {
                        'role': 'user',
                        'content': message,
                    },
                ])

        message_reply = ollama_result.get("message").get("content")
        return message_reply

    def get_flask_data(self, pathway, **kwargs):
        # Connect to Flask API to retrieve data from the server.
        base_url = f"{self.valves.FLASK_HOST}/{pathway}"
        params = None
        if kwargs.get("params"):
            params = kwargs.get("params")
        flask_data = None
        try:
            if params:
                response = requests.get(base_url, params=params)
            else:
                response = requests.get(base_url)
            # response.raise_for_status()  # Raise HTTPError for bad responses (4xx and 5xx)
            flask_data = response.json()
            try:
                flask_data = json.loads(flask_data)
            except:
                pass

        except requests.RequestException as e:
            error_response = f"An Error occurred: Flask Host: {self.valves.OLLAMA_HOST}, MESSAGE: {str(e)}."
            logging.error(f"Final message: {error_response}")

        return flask_data

    def send_post_request(self, pathway, data):
        # Convert your list of strings into JSON format.
        data_json = json.dumps(data)

        # Headers
        headers = {"Content-Type": "application/json"}

        # Specify the URL of the FastAPI endpoint
        url = f"{self.valves.FLASK_HOST}/{pathway}"

        try:
            # Send a POST request with the JSON payload.
            response = requests.post(url, headers=headers, json=data_json)

            # Check if the response was successful (200).
            response.raise_for_status()

            return response.json()

        except requests.RequestException as e:
            self.console_log(f'"An error occurred:\n" {str(e)}', "error")

    def console_log(self, message, logging_type):
        if logging_type == "info":
            logging.info(f"{message}")
        elif logging_type == "error":
            logging.error(f"{message}")

    def get_server_message(self):
        ollama_error_msg = f"An Error occurred: Ollama Host: {self.valves.OLLAMA_HOST}, is not reachable or running. Please check its configuration and try again."
        flask_error_msg = f"An Error occurred: FLASK Host: {self.valves.FLASK_HOST}, is not reachable or running. Please check its configuration and try again."
        if not self.ollama_status and not self.flask_status:
            return f"Both Servers are Unreachable: \n {ollama_error_msg}, \n {flask_error_msg}"
        elif not self.ollama_status:
            return ollama_error_msg
        elif not self.flask_status:
            return flask_error_msg

    def get_relevance_test(self, message):
        # Ask LLM if the request is valid to VFX Pipeline, Returns True if Yes or False if not.
        # First get the Prompt from Remote Server
        relevance_prompt = self.get_flask_data("relevance_prompt")
        relevance_prompt_construction = f"{relevance_prompt}{message}"
        # Send to LLM for item.
        relevance = self.connect_ollama(relevance_prompt_construction)
        return relevance

    def get_user_intent(self, message):
        # Ask LLM about the users intent to process.
        # First get the Prompt from Remote Server
        user_intent_prompt = self.get_flask_data("user_intent_prompt")
        user_intent_prompt_construction = f"{user_intent_prompt}{message}"
        # Send to LLM for item.
        user_intent = self.connect_ollama(user_intent_prompt_construction)
        return user_intent

    def setup_task(self, message):
        # Ask LLM for what Project/Sequence/Shot/Department/Person the SHot is going to be setup for.
        # Get Prompt from Server
        setup_prompt = self.get_flask_data("setup_prompt")  # Expects a JSON string back.
        setup_prompt_construction = f"{setup_prompt} {message}"
        setup_prompt_data = self.connect_ollama(setup_prompt_construction)

        setup_prompt_data = json.loads(setup_prompt_data)

        # Send Data to the Flask Server for setup.
        post_setup = self.send_post_request("create_workspace", data=setup_prompt_data)
        # Expect a json object with keys result, destination, template_used, error
        post_setup_data = json.loads(post_setup)

        if post_setup_data["result"]:
            return (f"Successfully Setup for {setup_prompt_data['user']} for the {setup_prompt_data['department']} at "
                    f"the path: \n {post_setup_data['destination']}")
        else:
            return (f"Unable to Setup for {setup_prompt_data['user']} for the {setup_prompt_data['department']}, "
                    f"Something went wrong:\n {post_setup_data['error']}.")

    def ingestion_task(self, message):
        # Ask LLM for what Project/Sequence/Shot/Department/Person the SHot is going to be setup for.
        items_processed = []

        # Get Prompt from Server for What type of Files its trying to ingest and return a dictionary of all items.
        ingestion_prompt = self.get_flask_data("ingestion_prompt")  # Expects a JSON string back.
        ingestion_prompt_construction = f"{ingestion_prompt} {message}"
        ingestion_prompt_data = self.connect_ollama(ingestion_prompt_construction)

        ingestion_prompt_data = json.loads(ingestion_prompt_data)
        """Example Data
            {
              "request1": {
                "project": "PROJ_ABC",
                "sequence": "Sequence11",
                "shot": "Shot1",
                "ingestion": ["plate", "rig"]
              },
              "request2": {
                "project": "PROJ_ABC",
                "sequence": "Sequence11",
                "shot": "Shot2",
                "ingestion": ["plate"]
              },
              "request3": {
                "project": "PROJ_XYZ",
                "sequence": "Seq1",
                "shot": "Shot2",
                "ingestion": ["mm"]
              }...
            }
        """
        # For each item in the JSON lib, Process request.
        if ingestion_prompt_data:
            for key, value in ingestion_prompt_data.items():
                value_data = value

                if not isinstance(value_data, dict):
                    continue

                # Construct a crude path for files in the project folder to process.
                # {root_drive_letter}://{project}/{sequence}/{shot}/{ingest}
                root_drive_letter = "T:\\"
                path_to_search = os.path.join(root_drive_letter,
                                              value_data["project"],
                                              value_data["sequence"],
                                              value_data["shot"],
                                              "ingest")
                folders_to_search = value_data["ingestion"]  # This is the folder to search for in the directory as a list.

                for folder in folders_to_search:

                    # Iterate over each item and process each department.
                    json_to_send = json.dumps({"search_path": path_to_search,
                                               "folders_to_search": folder})

                    # Send Data to the Flask Server for data back.
                    post_get_files_folders = self.send_post_request("get_files_folders", data=json_to_send)  # Expects JSON string back.
                    # Check the files returned to see if they are relevant via LLM.
                    # Expect a message back with the {"search_path": file_path,"files_found": files_data}
                    # Use LLM to process the JSON to send for Ingestion Request.

                    if isinstance(post_get_files_folders, str):
                        post_get_files_folders = json.loads(post_get_files_folders)

                    if post_get_files_folders["message"]:

                        extract_ingestion_info_prompt = self.get_flask_data("extract_ingestion_prompt")
                        extract_ingestion_info_prompt_construction = f"{extract_ingestion_info_prompt} {message}"
                        extract_ingestion_info_prompt_data = self.connect_ollama(extract_ingestion_info_prompt_construction)

                        extract_ingestion_info_prompt_data = json.loads(extract_ingestion_info_prompt_data)

                        """ Example Data
                        { 
                          "project": "PROJ_ABC",
                          "sequence": "abc11",
                          "shot": "sh001",
                          "department": "fx",
                          "type": "fx",
                          "is_sequence": true,
                          "src_path": "T:\\PROJ_ABC\\ingest\\plate",
                          "extension": "exr",
                          "naming_scheme": "fx",
                          "versioning": true,
                          "user": "pipeline"
                        }
                        """
                        # Process keys here if needed

                        ingestion_request_json = json.dumps(extract_ingestion_info_prompt_data)
                        # Send request with relevant data to the flask server
                        post_ingestion_request = self.send_post_request("ingest_request",
                                                                        data=ingestion_request_json)  # Expects JSON string back.
                        post_ingestion_request_data = json.loads(post_ingestion_request)

                        if post_ingestion_request_data["result"]:
                            # Successfull Ingestion
                            items_processed.append({"destination_path": post_ingestion_request_data["destination_path"],
                                                    "source_path": post_ingestion_request_data["source_path"],
                                                    "result": post_ingestion_request_data["result"]
                                                    })

        return items_processed  # Returns a list of dicts.

    def pipe(self, user_message: str, model_id: str, messages: List[dict], body: dict) -> Union[str, Generator, Iterator]:
        # This function is called when a new user_message is received.

        self.console_log("-/-Main Pipe-/-", "info")

        # Check for Heartbeat again
        self.heartbeat()  # Fast API server for the Queries and Ollama Server for LLM.

        self.console_log(f"Flask Status: {self.flask_status}", "info")
        self.console_log(f"Ollama Status: {self.ollama_status}", "info")

        # Init Final Response
        final_response = "..."

        # Check if flask and ollama servers are accepting connections, if not exit and return the error codes to user
        if not self.flask_status or not self.ollama_status:
            final_response = self.get_server_message()
            self.console_log(f"Error{final_response}", "error")  # log message to logs
            return final_response  # Return early to show errors before going through the rest of pipe.

        # Start

        # Check if the Response is a Valid Query for the VFX Pipeline. If not Forward it to the LLM instead and return its result.
        relevance_to_pipe = self.get_relevance_test(user_message)  # Should Return either a True or False Boolean Value.
        print(f"PipeRelevance: {relevance_to_pipe} : <EOF>")
        if "false" in relevance_to_pipe.lower():  # if it is NOT relevant to the Pipe.
            self.console_log("Forwarding non-relevant reply to LLM.", "info")  # log message to logs
            # Forward Request to the LLM or Cancel.
            llm_reply = self.connect_ollama(user_message)
            return llm_reply  # This end Prematurely to avoid executing rest of the code.
        else:
            # If users message is relevant try to process it
            # Ask the LLM if the User is requesting a Setup Request or an Ingestion Request.
            users_intent = self.get_user_intent(user_message)  # Should return a string of the department or "unsure" if it didnt understand.
            print(f"UserIntent: {users_intent} : <EOF>")
            if "unsure" in users_intent:
                unsure_message = "I'm sorry but I couldn't understand what to process, Can you repeat it clearly once again?"
                self.console_log(f"Final Response: {unsure_message}", "error")  # log message to logs
                return unsure_message

            # if the user is requesting a setup request
            if "setup" in users_intent:
                self.console_log("Setup Request Started.", "info")  # log message to logs
                # Start Setup Request
                setup_task = self.setup_task(user_message)
                print(f"SetupTask:{setup_task}")
                llm_reply = self.connect_ollama(f"Can you summarise the following message to a user that can better understand what happened: {setup_task}")
                return llm_reply

            # if the user is requesting an ingestion request
            if "ingestion" in users_intent:
                # handle ingestion control logic here.
                self.console_log("Ingestion Request Started.", "info")  # log message to logs
                ingestion_task = self.ingestion_task(user_message)
                print(f"IngestionTask:{ingestion_task}")
                llm_reply = self.connect_ollama(f"Can you create a message to the user showing the paths for items that were successfully ingesting into the pipeline? If its empty it means nothing was ingested.: {ingestion_task}")
                return llm_reply

        # End Result:
        self.console_log(f"Final Response: {final_response}", "info")  # log message to logs
        return final_response  # return final result message to the UI
