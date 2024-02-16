from flask import Flask, request, jsonify
from dotenv import load_dotenv
import requests
import os
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)
# Allow CORS and load env variables
load_dotenv()
CORS(app)
auth_token = os.environ.get("auth_token")
flask_passkey = os.environ.get("flask_passkey")

# Authorization and GET request headers for HTTP
headers = {
    "accept": "application/json",
    "authorization": f"Bearer {auth_token}",
}

# Stores all project gid's organized by year
yearmap = {
    "2025test": 1205653437109887,
    "2024": 1204275953504347,
    "2025": 1206530090972451,
}

# JSON payload template formatted properly for Asana
jsontemplate = {
    "data": {
        "projects": None,
        "name": None,
        "assignee": None,
        "start_on": None,
        "due_on": None,
        "custom_fields": {},
    }
}


# Authorize access to post route
@app.before_request
def authorize_user():
    if request.method == "POST" and request.path == "/post":
        provided_passkey = request.headers.get("Passkey")
        if provided_passkey != flask_passkey:
            return jsonify({"message": "Authentication failed"}), 401


# Accept incoming POST requests
@app.route("/post", methods=["POST"])
def post():
    try:
        # Extract the data object from the incoming POST request
        incomingJSONdata = request.get_json()
        print(incomingJSONdata)

        # Determine which conference year to POST to in Asana from incoming request
        schoolyear = str(
            datetime.strptime(incomingJSONdata["data"]["due_on"], "%m/%d/%Y %H:%M").year
        )

        yeargid = yearmap[schoolyear]

        # Get all tasks in the project currently in Asana
        target_api_url = f"https://app.asana.com/api/1.0/projects/{yeargid}/tasks?opt_fields=custom_fields.name,custom_fields.display_value"
        response = requests.get(target_api_url, headers=headers)
        hashmap = {}
        print(response.json())
        for item in response.json()["data"]:
            # print(item)
            for element in item["custom_fields"]:
                if "StarRez Event ID" in element.values():
                    if element["display_value"] != None:
                        hashmap[element["display_value"]] = item["gid"]
        print(hashmap)

        # If Event Name from Star RezJSON is already in Asana, lookup and return its GID
        EventID = incomingJSONdata["data"]["StarRez Event ID"]
        if not isUniqueEventID(hashmap, EventID):
            taskgid = getGidFromMap(hashmap, EventID)

        # Take the incoming JSON data, and format it
        formatstd = format_standardfields(incomingJSONdata, yeargid)
        formatcust = format_customfields(incomingJSONdata, yeargid)
        #  Populate our json template with its information
        fulloutput = create_modified_template(formatstd)
        fulloutput["data"]["custom_fields"] = formatcust
        print("print formatted customfields")
        print(formatcust)
        print(fulloutput)

        # Post request if incoming event is "unique", Put request if incoming event already exists
        if isUniqueEventID(hashmap, EventID):
            post_request_to_asana(fulloutput)
            print("posting")
            return "passed"
        else:
            print("Updating taskgid:" + taskgid)
            put_request_to_asana(taskgid, fulloutput)

        return ""
    except Exception as e:
        #     # Handle any exceptions that may occur during processing
        return jsonify({"error": str(e)}), 500


# Returns the school year of a given a datetime object
def get_school_year(date):
    try:
        if date.month >= 8:
            return str(date.year)
        else:
            return str(date.year - 1)

    except Exception as e:
        return None


# Requires a field map and a formatted JSON dict, and creates an output dict for Asana
def create_modified_template(formatted_template):
    output = jsontemplate.copy()
    print(formatted_template.items())
    for key, value in formatted_template.items():
        output["data"][key] = value

    return output


# Helper to format standard fields section of JSON template
def format_standardfields(starRezJSON, projectgid):
    formattedJSON = {}
    startdate = format_date(starRezJSON["data"].get("start_on"))
    enddate = format_date(starRezJSON["data"].get("due_on"))
    print(startdate)
    print(enddate)
    if (startdate is not None) and (enddate is None):
        formattedJSON["start_on"] = None
        formattedJSON["due_on"] = None
    else:
        formattedJSON["start_on"] = startdate
        formattedJSON["due_on"] = enddate
    formattedJSON["projects"] = str(projectgid)
    formattedJSON["name"] = format_text(starRezJSON["data"].get("name"))
    formattedJSON["assignee"] = format_assignee(starRezJSON["data"].get("assignee"))
    return formattedJSON


# Helper to format custom fields section of modified JSON template
def format_customfields(input, projectgid):
    customfieldmap = {}
    boolmap = {}
    output = {}
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {auth_token}",
    }
    target_api_url = (
        f"https://app.asana.com/api/1.0/projects/{projectgid}/custom_field_settings"
    )
    response = requests.get(target_api_url, headers=headers)

    # Create customfieldmap, map custom field names to their gid at index 0 and type at index 1
    for item in response.json()["data"]:
        customfieldmap[item["custom_field"]["name"]] = [
            item["custom_field"]["gid"],
            item["custom_field"]["resource_subtype"],
        ]

    # Format bools
    for custom_field_setting in response.json()["data"]:
        if (
            "custom_field" in custom_field_setting
            and "enum_options" in custom_field_setting["custom_field"]
        ):
            enum_options = custom_field_setting["custom_field"]["enum_options"]
            # Check if both "Yes" and "No" are present in enum options
            yes_present = any(option["name"] == "Yes" for option in enum_options)
            no_present = any(option["name"] == "No" for option in enum_options)

            if yes_present and no_present:
                boolmap[custom_field_setting["custom_field"]["name"]] = [
                    custom_field_setting["custom_field"]["gid"],
                    custom_field_setting["custom_field"]["enum_options"][0]["gid"],
                    custom_field_setting["custom_field"]["enum_options"][1]["gid"],
                ]

    print("bool")
    print(boolmap)
    print("customfieldmap")
    print(customfieldmap)

    # Iterate through customfield map and choose correct formatting function
    for custom_field in input["data"]:
        print("customfields:")
        print(custom_field)
        # Mapping custom fields with Yes/No options to True and False
        if custom_field in boolmap:
            if input["data"][str(custom_field)] == "True":
                output[boolmap[custom_field][0]] = boolmap[custom_field][1]
            elif input["data"][str(custom_field)] == "False":
                output[boolmap[custom_field][0]] = boolmap[custom_field][2]
        # Mapping custom fields with Date requirements to be formatted properly
        elif (
            str(custom_field) in customfieldmap
            and customfieldmap[str(custom_field)][1] == "date"
        ):
            output[customfieldmap[str(custom_field)][0]] = format_customfielddate(
                input["data"][custom_field]
            )
        # Mapping all other custom fields (excluding enum and multi-enum fields) to string format
        elif (
            str(custom_field) in customfieldmap
            and customfieldmap[str(custom_field)][1] != "enum"
        ) and (
            str(custom_field) in customfieldmap
            and customfieldmap[str(custom_field)][1] != "multi_enum"
        ):
            output[customfieldmap[str(custom_field)][0]] = input["data"][
                str(custom_field)
            ]

    return output


# Helper to retrieve an Asana task GID given an Event Name
def getGidFromMap(eventmap, target_id):
    try:
        return eventmap[target_id]
    except KeyError as e:
        return None


# Returns whether or not an Event is Unique in EventList
def isUniqueEventID(eventmap, eventName):
    return getGidFromMap(eventmap, eventName) is None


# Returns EventName given a StarRez event
def getEventItem(starRezDict, key):
    return starRezDict[key]


# Sends a POST request to Asana with given JSON payload
def post_request_to_asana(payload):
    target_api_url = "https://app.asana.com/api/1.0/tasks"
    response = requests.post(target_api_url, json=payload, headers=headers)
    print("POSTING")
    # Debugging print statements
    # print(response.json())
    # print(response.json()["data"]["name"])


# Sends a PUT request to Asana with given JSON payload
def put_request_to_asana(taskgid, payload):
    payload["data"].pop("projects")
    target_api_url = f"https://app.asana.com/api/1.0/tasks/{taskgid}"
    response = requests.put(target_api_url, json=payload, headers=headers)
    print("PUTTING")
    # Debugging print statements
    # print(response)
    # print(response.json())


# Formats a date in YMD format if parseable, otherwise returns None.
def format_date(input_date):
    try:
        # Parse the input date string
        parsed_date = datetime.strptime(input_date, "%m/%d/%Y %H:%M")

        # Format the date into yyyy-mm-dd format
        formatted_date = parsed_date.strftime("%Y-%m-%d")

        return formatted_date

    except ValueError as e:
        print(str(e))
        # Handle the exception if the date string is not in the expected format
        return None


# Formats custom fields date in YMD format if parseable, otherwise returns None.
def format_customfielddate(input_date):
    output = {}
    try:
        # Parse the input date string
        parsed_date = datetime.strptime(input_date, "%m/%d/%Y %H:%M")

        # Format the date into yyyy-mm-dd format
        output["date"] = parsed_date.strftime("%Y-%m-%d")

        return output

    except ValueError as e:
        print(str(e))
        # Handle the exception if the date string is not in the expected format
        return None


# Formats a num field, otherwise returns None
def format_nums(input_int):
    try:
        return int(input_int)
    except ValueError:
        return None


# Formats a bool field, otherwise returns None
def format_bool(input_bool):
    try:
        return bool(input_bool)
    except ValueError:
        return None


# Formats a text field, otherwise returns None
def format_text(input_text):
    try:
        return str(input_text)
    except ValueError:
        return "Error Auto-Updating Task (Please Fix Manually)"


# Formats an assignee field, otherwise returns None
def format_assignee(assignee):
    if isinstance(assignee, str):
        return assignee
    else:
        return None


if __name__ == "__main__":
    app.run(port="5000", debug=True)
