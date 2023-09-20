import json
import re
import os
import datetime
import json
import re
import os
import datetime
from fuzzywuzzy import fuzz
import sys
# Function to perform text cleaning
def clean_text(text):
    cleaned_text = ' '.join(text.split())
    return cleaned_text

# Function to extract email from text using regular expression
def extract_email(text):
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
    match = re.search(email_pattern, text)
    if match:
        return match.group()
    else:
        return "None"

def extract_phone(text):
    # Define a regular expression pattern to match phone numbers with at least 9 digits
    phone_pattern = r'(?<!\d)(?:(?:\+\d{1,4}[-.\s]?)?(?:\(\d{1,5}\)[-.\s]?)?)?\d{3,}[-.\s]?\d{3,}[-.\s]?\d{3,}(?!\d)'
    
    # Search for the pattern in the text
    match = re.search(phone_pattern, text)
    
    if match:
        # Clean up the matched phone number by removing separators
        phone_number = re.sub(r'[-.\s]', '', match.group())
        return phone_number
    else:
        return "None"

# Function to extract location information from the resume data
def extract_location(resume_data):
    for data_set in resume_data["data"]:
        locations = data_set.get("LOCATION", [])
        if locations:
            return locations[0]
    return "None"

# Function to perform fuzzy matching on keys
def fuzzy_match_key(input_dict, target_key):
    highest_score = 0
    matched_key = None
    for key in input_dict.keys():
        score = fuzz.ratio(key.lower(), target_key.lower())
        if score > highest_score:
            highest_score = score
            matched_key = key
    return matched_key

# Define the get_clean_name_from_file_path function
def get_clean_name_from_file_path(file_path):
    file_name = os.path.basename(file_path)
    name_parts = file_name.split(".")
    if len(name_parts) > 1:
        name = name_parts[0]
    else:
        name = file_name
    name_without_numbers = ''.join(filter(lambda x: not x.isnumeric(), name))
    name_cleaned = name_without_numbers.strip('_').lower()
    file_name, extension = os.path.splitext(os.path.basename(file_path))
    return name_cleaned, file_name[:-len("_0")]

# Function to reformat the input data
def reformat_data(input_file_path):
    with open(input_file_path, 'r', encoding='utf-8') as input_file:
        input_data = json.load(input_file)

    reformatted_data = []

    for data_set in input_data["data"]:
        image_path = data_set["image_path"]

        image_path_data = []

        for set_data in data_set["data"]:
            fulltext = set_data["fulltext"]

            text_fields_data = {field["class_name"]: field["text"] for field in set_data["text_fields"]}

            set_reformatted_data = {
                "fulltext": fulltext,
                "text_fields": text_fields_data
            }

            image_path_data.append(set_reformatted_data)

        image_path_reformatted_data = {
            "image_path": image_path,
            "data": image_path_data
        }

        reformatted_data.append(image_path_reformatted_data)

    output_data = {"data": reformatted_data}

    return output_data

# Function to process the reformatted data
def process_reformatted_data(reformatted_data):
    processed_resumes = []

    for resume_data in reformatted_data["data"]:
        all_full_text = ""
        for data_set in resume_data["data"]:
            all_full_text += data_set.get("fulltext", "") + "\n"

        professional_summary = ""
        for data_set in resume_data["data"]:
            if "PRO_SUMMARY" in data_set["text_fields"]:
                professional_summary = data_set["text_fields"]["PRO_SUMMARY"]
                break

        cleaned_text = clean_text(all_full_text)

        current_location = extract_location(resume_data)

        current_datetime = datetime.datetime.now().isoformat()

        words_count = len(cleaned_text.split())
        line_count = len(all_full_text.split('\n'))

        name_cleaned, file_name = get_clean_name_from_file_path(resume_data["image_path"])

        resume_ksat_entries = []

        for data_set in resume_data["data"]:
            has_ksat_info = (
                sum(field in data_set["text_fields"] for field in ["KSAT SECTION", "JOB TITLE", "COMPANY", "PROJECT DURATION"]) >= 2
            )

            if has_ksat_info:
                ksat_entry = {
                    "fullTextKSAT": data_set["text_fields"].get("KSAT SECTION", "None"),
                    "jobTitleKSAT": data_set["text_fields"].get("JOB TITLE", "None"),
                    "companyKSAT": data_set["text_fields"].get("COMPANY", "None"),
                    "projectDurationKSAT": data_set["text_fields"].get("PROJECT DURATION", "None"),
                }
                resume_ksat_entries.append(ksat_entry)

        output_json = {
            "profile": {
                "Name": name_cleaned,
                "email": extract_email(all_full_text),
                "phone": extract_phone(all_full_text),
                "current location": current_location
            },
            "professional summary": professional_summary,
            "professional qualification": resume_data["data"][0]["text_fields"].get("JOB TITLE", "None"),
            "professional experience": resume_data["data"][0]["text_fields"].get("PRO_EXP", "None"),
            "overallSkills": "None",
            "other information": {
                "reference": "None",
                "militaryHistory": "None",
                "accomplishment": "None",
                "extraCurricular": "None",
                "Publications": {
                    "patents": {"None"},
                    "papers": {"None"}
                },
                "resumeFullText": cleaned_text,
                "resumeKSATs": resume_ksat_entries,
                "certifications": "None",
                "courses": "None",
                "education": {
                    "educationDegree": "None",
                    "educationCollege":"None",
                    "education1Duration": "None",
                    "specialization": "None"
                }
            },
            "metaData": {
                "originalFileName": file_name,
                "dataTimeReceived": current_datetime,
                "wordsCount": words_count,
                "lineCount": line_count,
                "fileLocation": resume_data["image_path"]
            }
        }

        processed_resumes.append(output_json)

    return processed_resumes

# Define a function to make data JSON-serializable
def convert_to_serializable(data):
    if isinstance(data, set):
        return list(data)
    elif isinstance(data, dict):
        return {key: convert_to_serializable(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_to_serializable(item) for item in data]
    else:
        return data

# Define a function to save JSON data to a file with an incremented filename
def save_json_to_incremented_file(data, folder_path):
    # Create the folder if it doesn't exist
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # Set the base filename
    base_filename = "standard_json.json"
    output_file_path = os.path.join(folder_path, base_filename)

    # Check if the file with the base filename already exists
    file_exists = os.path.isfile(output_file_path)

    # If the file exists, increment the filename
    if file_exists:
        # Find the next available filename by incrementing a number
        counter = 1
        while True:
            incremented_filename = f"standard_json_{counter}.json"
            output_file_path = os.path.join(folder_path, incremented_filename)
            if not os.path.isfile(output_file_path):
                break
            counter += 1

    with open(output_file_path, 'w', encoding='utf-8') as output_file:
        json.dump(data, output_file, ensure_ascii=False, indent=2)

    return output_file_path
def main():
    if len(sys.argv) > 1:
        input_json_path = sys.argv[1]
    else:
        input_json_path = input("Enter the input JSON file path: ")

    # Call the reformat_data function to get the reformatted data
    reformatted_data = reformat_data(input_json_path)

    # Call the process_reformatted_data function with the reformatted data
    processed_resumes = process_reformatted_data(reformatted_data)  # Select the first element

    # Convert the processed data to a JSON-serializable format
    json_serializable_data = convert_to_serializable(processed_resumes)
    # Specify the folder path where you want to save the JSON files
    output_folder_path = r'D:\standard_json_of_resume'

    # Call the save_json_to_incremented_file function to save the processed data with an incremented filename
    output_json_file_path = save_json_to_incremented_file(json_serializable_data, output_folder_path)

    # Print the path to the saved JSON file
    print("Processed data saved to:", output_json_file_path)

if __name__ == "__main__":
    main()
