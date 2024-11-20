import os
import json
import shutil
import re
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Request, Body, Path
from pydantic import BaseModel

app = FastAPI()

# Define the GET endpoints
@app.get("/ping")
async def ping():
    return {"message": "Pong!"}


@app.get("/relevance_prompt")
async def relevance_prompt():
    relevance_prompt_file = "prompts/relevance_prompt.txt"
    # content = await read_file(relevance_prompt_file)  # async implementation
    content = read_file(relevance_prompt_file)
    if content:
        return {"message": f"{content}"}
    else:
        return {"error": f"Could not read Prompt File: {relevance_prompt_file}."}


@app.get("/user_intent_prompt")
async def user_intent_prompt():
    user_intent_prompt_file = "prompts/user_intent.txt"
    content = read_file(user_intent_prompt_file)
    if content:
        return {"message": f"{content}"}
    else:
        return {"error": f"Could not read Prompt File: {user_intent_prompt_file}."}


@app.get("/setup_prompt")
async def setup_prompt():
    setup_prompt_file = "prompts/setup_prompt.txt"
    content = read_file(setup_prompt_file)
    if content:
        return {"message": f"{content}"}
    else:
        return {"error": f"Could not read Prompt File: {setup_prompt_file}."}


@app.get("/ingestion_prompt")
async def setup_prompt():
    setup_prompt_file = "prompts/ingestion_prompt.txt"
    content = read_file(setup_prompt_file)
    if content:
        return {"message": f"{content}"}
    else:
        return {"error": f"Could not read Prompt File: {setup_prompt_file}."}


@app.get("/extract_ingestion_prompt")
async def extract_ingestion_prompt():
    setup_prompt_file = "prompts/extract_ingestion_prompt.txt"
    content = read_file(setup_prompt_file)
    if content:
        return {"message": f"{content}"}
    else:
        return {"error": f"Could not read Prompt File: {setup_prompt_file}."}


def read_file(file_path):
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return None


# async def read_file(file_path):
#     import aiofiles
#     try:
#         async with aiofiles.open(file_path, 'r') as f:
#             content = await f.read()
#             return content.decode('utf-8')
#     except FileNotFoundError:
#         return None

@app.post("/create_workspace")
async def create_workspace(request: Request):
    data = await request.json()
    data = json.loads(data)  # Convert to dict and then to JSON
    print(data)

    """ Example Structure
    {
        "project": "PROJ_ABC",
        "sequence": "Seq2",
        "shot": "Shot1",
        "department": "fx",
        "user": "Alice"
    }
    """
    # Init
    completed_status = False
    project_folder_path = None
    template_root_path = None
    errors = None
    # Craft Path
    root_temp_drive = "T:\\"
    root_project_drive = "P:\\"

    try:
        project_folder_path = os.path.join(root_project_drive, *data.values())
    except TypeError:
        return json.dumps({"result": False})
    # CHeck if this folder exists:
    if not os.path.exists(project_folder_path):
        project_folder_path = os.path.join(project_folder_path, "v0001")  # Create a v0001 folder as it didnt exist.
    else:
        # Get all folders that match the regex v0001
        # List all directories in the folder
        dirs = [d for d in os.listdir(project_folder_path) if os.path.isdir(os.path.join(project_folder_path, d))]
        # Filter directories with the pattern vXXXX
        v_dirs = [d for d in dirs if re.match(r'v\d{4}', d)]
        # Extract the number from each directory name and convert it to an integer
        numbers = [int(re.sub(r'[a-z]', '', d)) for d in v_dirs]
        # Get the largest number
        try:
            max_number = max(numbers)
        except ValueError:
            max_number = 0
        project_folder_path = os.path.join(project_folder_path, f"v{(str(max_number+1)).zfill(4)}")

    # Create folder(s)
    try:
        os.makedirs(project_folder_path, exist_ok=True)
    except Exception as e:
        errors += f"Error creating {str(project_folder_path)}: {e}\n"

    # Copy the template folder from the template section:
    template_root_path = os.path.join(root_temp_drive, "Templates", data["department"])  # T:\Templates\{department}
    project_folder_path = os.path.join(project_folder_path, data["department"])  # project_folder_path\{department}
    # Check if the Department path exists for this
    if os.path.exists(template_root_path):
        # Copy over the folder.
        try:
            print(template_root_path, project_folder_path)
            shutil.copytree(template_root_path, project_folder_path)
            completed_status = True
        except Exception as e:
            print(e)
            errors += f"Error creating {str(project_folder_path)}: {str(e)}\n"

    # Handle Return Data:
    result = {
        "result": completed_status,
        "destination": project_folder_path,
        "template_used": template_root_path,
        "error": errors
    }
    # Convert to json String
    result = json.dumps(result)
    return result


def get_files_in_directory(directory, extension_filter=None):
    """
    Detects file sequences dynamically in a directory and returns compact representations as tuples.

    Args:
        directory (str): The directory to scan for files.
        extension_filter (str, optional): File extension to filter files (e.g., '.exr', '.jpg').
                                          If None, all files are considered.

    Returns:
        list: A list of tuples for file sequences or individual filenames.
              Each tuple contains the first and last file in a sequence.
    """
    # List all files in the directory
    files = os.listdir(directory)

    # Filter files by extension if specified
    if extension_filter:
        files = [file for file in files if file.endswith(extension_filter)]

    # Dictionary to group sequences by base name
    sequences = defaultdict(list)
    other_files = []

    # Regular expression to detect numbers in filenames
    dynamic_pattern = re.compile(r"^(.*?)(\d+)(\.\w+)$")

    for file in files:
        match = dynamic_pattern.match(file)
        if match:
            base_name = match.group(1)  # Base name without numbers
            frame_index = int(match.group(2))  # Extract numerical part
            extension = match.group(3)  # File extension
            sequences[(base_name, extension)].append((frame_index, file))
        else:
            other_files.append(file)

    # Create compact sequence representations
    compact_files = []
    for (base_name, extension), frames in sequences.items():
        frames.sort()  # Sort by frame index
        if len(frames) > 1:  # If a sequence exists
            compact_files.append((frames[0][1], frames[-1][1]))  # Add first and last files as a tuple
        else:  # Single frame, treat as a regular file
            compact_files.append(frames[0][1])

    # Add non-sequence files to the result
    compact_files.extend(other_files)
    return compact_files


@app.post("/get_files_folders")
async def get_files_folders(request: Request):
    data = await request.json()
    data = json.loads(data)
    print(data)
    print(type(data))
    if not isinstance(data, dict):
        data = json.loads(data)  # Convert to dict and then to JSON
    print(type(data))

    """ Example
    {"search_path": path_to_search,
    "folders_to_search": folders_to_search}
    """
    # Start
    return_dict = {}
    files_data = None
    file_path = ""
    try:
        search_path = data["search_path"].replace("\\", "/")
        folder_seach = data["folders_to_search"]
        file_path = os.path.join(search_path, folder_seach)
        files_data = get_files_in_directory(file_path)
    except:
        return_dict = {"error": f"An Error Occurred with searching the path: {file_path}."}

    if files_data:
        data_dict = {"search_path": file_path,
                     "files_found": files_data}
        return_dict = {"message": data_dict}

    return json.dumps(return_dict)


@app.post("/ingest_request")
async def ingest_request(request: Request):
    data = await request.json()
    data = json.loads(data)  # Convert to dict and then to JSON
    if not isinstance(data, dict):
        data = json.loads(data)  # Convert to dict and then to JSON
    print(data)

    """ Example Single File Structure
    {
        "project": "PROJ_ABC",
        "sequence": "Seq2",
        "shot": "Shot1",
        "department": "fx",
        "type" : "houdini_scene",
        "is_sequence": false,
        "src_path": "T:\\PROJ_ABC\\ingest\\fx",
        "extension": "hip",
        "naming_scheme":"scene",
        "versioning": true,
        "user": "Alice"
    }
    """
    """ Example File Sequence Structure
        {
            "project": "PROJ_ABC",
            "sequence": "Seq2",
            "shot": "Shot1",
            "department": "plate",
            "type" : "plate",
            "is_sequence": true,
            "src_path": "T:\\PROJ_ABC\\ingest\\plate",
            "extension": "exr",
            "naming_scheme":"plate_main",
            "versioning": true,
            "user": "Alice"
        }
        """

    # Init
    completed_status = False
    errors = None
    destination_path = None

    # Start

    # Handle the path to create.
    # Construct new path from logic
    root_temp_drive = "T:\\"
    root_project_drive = "P:\\"

    ingestion_path = os.path.join(root_project_drive,
                                  data["project"],
                                  data["sequence"],
                                  data["shot"],
                                  data["department"],
                                  data["type"],
                                  data["naming_scheme"]
                                  )

    # Add versioning if specified.
    if data["naming_scheme"]:
        # Check if the path exists and if so get all versions.
        # CHeck if this folder exists:
        if not os.path.exists(ingestion_path):
            ingestion_path = os.path.join(ingestion_path, "v0001")  # Create a v0001 folder as it didnt exist.
            version = "v0001"
        else:
            # Get all folders that match the regex v0001
            # List all directories in the folder
            dirs = [d for d in os.listdir(ingestion_path) if os.path.isdir(os.path.join(ingestion_path, d))]
            # Filter directories with the pattern vXXXX
            v_dirs = [d for d in dirs if re.match(r'v\d{4}', d)]
            # Extract the number from each directory name and convert it to an integer
            numbers = [int(re.sub(r'[a-z]', '', d)) for d in v_dirs]
            # Get the largest number
            try:
                max_number = max(numbers)
            except ValueError:
                max_number = 0
            version = f"v{(str(max_number + 1)).zfill(4)}"
            ingestion_path = os.path.join(ingestion_path, version)

    # Handle the File renaming and Copy.
    # If it's a file extract the file name from the src_path as it expects a full path to the file.
    source_path = data["src_path"]
    #Convert to Windows Path
    source_path = source_path.replace("/", "\\")
    drive_letter = source_path[0]
    source_path = source_path.replace(f"{drive_letter}:/", f"{drive_letter}:\\\\")

    if not data["is_sequence"]:

        # Is expected to be a file.
        if os.path.exists(source_path):  # Check if file exists
            if os.path.isfile(source_path):  # Check if the path is a file.
                # Construct a new name for the file to copy.
                if data["versioning"]:
                    # {naming_scheme}_{version}.{ext}
                    new_file_name = f'{data["naming_scheme"]}_{version}.{data["ext"]}'
                else:
                    # {naming_scheme}.{ext}
                    new_file_name = f'{data["naming_scheme"]}.{data["ext"]}'
                destination_full_path = os.path.join(ingestion_path, new_file_name)

                # Copy File command
                os.makedirs(ingestion_path, exist_ok=True)
                shutil.copy2(source_path, destination_full_path)
                completed_status = True
                destination_path = destination_full_path
    else:

        # Folder Ingestion.
        # Is expected to be a folder.
        if os.path.exists(source_path):  # Check if path exists
            if os.path.isdir(source_path):  # Check if the path is a folder.
                # Find everything with relevant ext
                ext = data["extension"]
                relevant_files = [filename for filename in os.listdir(source_path) if filename.endswith(f".{ext}")]  # Should return a list of all files in the folder matching the ext
                if relevant_files:
                    # Construct a new name for the file to copy.
                    file_number = 0

                    for i in range(len(relevant_files)):
                        file_number += 1
                        file_number_offset = 1000
                        file_number_string = str(file_number + file_number_offset)
                        if data["versioning"]:
                            new_file_name = f'{data["naming_scheme"]}_{version}.{file_number_string}.{ext}'
                        else:
                            new_file_name = f'{data["naming_scheme"]}.{file_number_string}.{ext}'
                        destination_full_path = os.path.join(ingestion_path, new_file_name)
                        source_path_file = os.path.join(source_path, relevant_files[i])
                        # Copy File command
                        print(source_path_file, destination_full_path)
                        os.makedirs(ingestion_path, exist_ok=True)
                        shutil.copy2(source_path_file, destination_full_path)

                    if file_number == len(relevant_files):
                        completed_status = True
                    destination_path = ingestion_path

    # Handle Return Data:
    result = {
        "result": completed_status,
        "destination_path": destination_path,
        "source_path": source_path,
        "error": errors
    }
    # Convert to json String
    result = json.dumps(result)
    return result


if __name__ == "__main__":
    # Run the app with Uvicorn as the ASGI server
    import uvicorn

    uvicorn.run(app, host="localhost", port=5000)
