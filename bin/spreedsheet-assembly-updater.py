import gspread
import pprint
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import requests

def create_url_column(sheet):

    # get all the records of the data
    records_data = sheet.get_all_records()

    # convert the json to dataframe
    df = pd.DataFrame.from_dict(records_data)

    # list to store URL columm
    url = list()

    # analyse each assembly stated in the first column
    for assembly_id in df.iloc[:, 0]:
        gca_number = assembly_id[assembly_id.find('GCA_')::]
        #check if webpage exists
        response = requests.get(f'https://www.ebi.ac.uk/ena/browser/view/{gca_number}')

        if response.status_code == 200:
            url.append(f'https://www.ebi.ac.uk/ena/browser/api/fasta/{gca_number}?download=true&gzip=true')
        else:
            url.append(f'URL for {gca_number} not working')

        print(f'{gca_number} -> {assembly_id} -> {url[-1]} ')

    sheet.insert_cols([['URL'] + url], len(df.columns))

if __name__ == "__main__":
    # define the scope
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

    # add credentials to the account
    creds = ServiceAccountCredentials.from_json_keyfile_name('/Users/thiagogenez/Documents/github/assembly-spreedsheet/python-assembly-sheets-f44deb645429.json', scope)

    # authorize the clientsheet
    client = gspread.authorize(creds)

    # get the spreadsheet by the filename
    sheet = client.open('test Assembly for alignment')

    # analyse all spreadsheets
    for sh in sheet.worksheets():
        create_url_column(sh)

