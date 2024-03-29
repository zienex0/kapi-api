import requests

def read_spreadsheet_data(access_token, spreadsheet_id, range_name):
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name}'

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        values = data.get('values', [])
        return {'success': True, 'data': values}
    else:
        return {'success': False, 'message': response.json()}


def append_row_to_spreadsheet(access_token, col_names, spreadsheet_id, range_name, json_data):
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name}:append?valueInputOption=USER_ENTERED'
    
    headers = {
         'Authorization': f'Bearer {access_token}',
         'Content-Type': 'application/json',
    }

    row_values = [""] * len(col_names)
    for key, value in json_data.items():
        if key in col_names:  
            index = col_names.index(key)
            row_values[index] = value

    body = {"values": [row_values]}

    response = requests.post(url, headers=headers, json=body)
    if response.status_code == 200:
        data = response.json()
        return {'success': True, 'data': data}
    else:
        return {'success': False, 'message': response.json()}
