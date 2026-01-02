import requests
import urllib3
import json
import os

# 1. Get configuration from Environment Variables
# These will be passed from your GitHub Action workflow
repository_url = os.environ.get('NEXUS_URL')
source_repository = os.environ.get('NEXUS_REPO')
file_name = os.environ.get('JSON_FILE_NAME', 'general_packages.json')

# Construct base URL
source_url = f"{repository_url}/service/rest/v1/components?repository={source_repository}"

# Disable SSL warnings for self-hosted Nexus with self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

unique_packages = {}
nx_token = None
read_again = True

print(f"Starting fetch from {source_repository}...")

while read_again:
    url = source_url
    if nx_token:
        url = f"{source_url}&continuationToken={nx_token}"
    
    print(f"Fetching page: {url}")
    
    try:
        response = requests.get(url, verify=False)
        response.raise_for_status() # Raise error for bad status codes
        results = response.json()
        
        items = results.get('items', [])
        
        for item in items:
            pkg_name = item.get('name')
            pkg_group = item.get('group')
            
            # Format the NPM name (handles scoped vs unscoped)
            # If group exists, it usually maps to @group/name
            if pkg_group:
                npm_name = f"@{pkg_group}/{pkg_name}"
            else:
                npm_name = pkg_name

            # Deduplication logic: Use pkg_name as key to ensure uniqueness
            if pkg_name not in unique_packages:
                unique_packages[pkg_name] = {
                    "group": pkg_group,
                    "name": pkg_name,
                    "npm": npm_name
                }

        nx_token = results.get('continuationToken')
        if not nx_token:
            read_again = False
            print('Done! No more pages to read.')
            
    except Exception as e:
        print(f"Error calling Nexus: {e}")
        exit(1)

# 2. Transform dictionary back to the list structure you requested
output_data = {
    "packages": list(unique_packages.values())
}

# 3. Write to file
with open(file_name, "w") as f:
    json.dump(output_data, f, indent=4)

print(f"Successfully generated {file_name} with {len(output_data['packages'])} unique packages.")