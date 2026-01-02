import json

def extract_s_values(json_file_path):
    """
    Reads a JSON file, parses it as a list of objects,
    and prints the value for the 's' key from each object.
    """
    try:
        # Open and read the JSON file
        with open(json_file_path, 'r') as f:
            data = json.load(f)
        
        # Check if data is a list
        if not isinstance(data, list):
            print(f"Error: JSON content in {json_file_path} is not a list.")
            return

        # Iterate over each item in the list
        for item in data:
            # Check if the item is a dictionary (object) and has the 'symbol' key
            if isinstance(item, dict) and 'symbol' in item:
                # Print the value of the 'symbol' key
                print(item['symbol']+"1!")
            else:
                print(f"Warning: Found an item without a 'symbol' key or not an object: {item}")

    except FileNotFoundError:
        print(f"Error: The file {json_file_path} was not found.")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {json_file_path}.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    # The script assumes the JSON file is named 'data.json'
    # and is in the same directory.
    extract_s_values('data.json')