#Borrower registration script.
#Author Rachel Merrick
#Retrives new  Libwizard form data with API. Extracts relevant data from the Libwizard API response, places relevant
#fields into a JSON object to send to an Alma API to then create the users in Alma.

#Import libraries
import requests as req #Used to to access Alma API.
from requests.structures import CaseInsensitiveDict #used to create and send JSON request data object.
import pandas as pd #Used to create data frame.
import random #Used to create barcode
import re #Allows use of regular expresions which have been used to extract error messages.
from datetime import datetime, timedelta, timezone #Used to set expiry and purge dates based on the current date.

#Libwizard API data
auth_server_url = '' #URL used to get authentication token, enter relevant details
client_id = '' #Enter relevant details
client_secret = '' #Enter relevant details
form_id = ''#Enter relevant details
form_url = '' + form_id #URL used to get form details, enter relevant details
token_grant_type = {'grant_type': 'client_credentials'}
token_response = req.post(auth_server_url,
                          data=token_grant_type, verify=False, allow_redirects=False,
                          auth=(client_id, client_secret)) #API request to retrieve authentication token.
token_message = '{"access_token":"(.+?)",' #Regualr expression to identify token from API response
token_check = re.search(token_message, token_response.text) #Regex search to retrieve token from API response
token = token_check.group(1) #Assign token to varibale
api_call_headers = {'Authorization': 'Bearer ' + token} #form API call headers
form_response = req.get(form_url, headers=api_call_headers, verify = False) #Get request to retrive form details.

#Check if libwizard from response contains any records, if not print messaging no forms found.
if form_response.text == '[]':
    print('No completed forms found in libwizard.')

#Else there are records and continue processing script.
else:

    #Alma API data
    api_alma = '' #Alma production api key, enter relevant details
    alma_url = ('https://api-ap.hosted.exlibrisgroup.com/almaws/v1/users?social_authentication='+
                'false&send_pin_number_letter=false&apikey=' + api_alma) #Alma post user API URL
    alma_headers = CaseInsensitiveDict() #Used to send JSON portfolio object.
    alma_headers["Content-Type"] = "application/json" #Used to send JSON user object.

    #Variables used to detect and report Alma API errors.
    alma_url_error = '<errorsExist>true</errorsExist>' #Test to indicate when an error is pressent in API request url.
    alma_error_message = '<errorMessage>(.+)</errorMessage>' #Extracting the error message from API response.
    alma_data_object_error = '"errorsExist":true' #Test to indicate when an error is pressent in JSON data object.

    #Use regular expressions to extract relevant user data Libwizard form response and put them into lists for each attribute.
    form_instance_id = re.findall('"instanceId":(\d+),"created"', form_response.text)
    surname = re.findall('fieldId":2940111,"data":"(.*?)"', form_response.text)
    first_name = re.findall('fieldId":2940112,"data":"(.*?)"', form_response.text)
    address = re.findall('fieldId":2940113,"data":"(.*?)"', form_response.text)
    suburb = re.findall('fieldId":2940116,"data":"(.*?)"', form_response.text)
    state = re.findall('fieldId":2947974,"data":"(.*?)"', form_response.text)
    postcode = re.findall('fieldId":2940117,"data":"(.*?)"', form_response.text)
    email = re.findall('fieldId":2940114,"data":"(.*?)"', form_response.text)
    phone = re.findall('fieldId":2940119,"data":"(.*?)"', form_response.text)
    library = re.findall('fieldId":2947927,"data":"(.*?)"', form_response.text)
    user_group = re.findall('fieldId":2940109,"data":"(.*?)"', form_response.text)
    reciprocal_institution = re.findall('fieldId":2947933,"data":"(.*?)"', form_response.text)
    privacy_version = re.findall('fieldId":2956002,"data":"(.*?)"', form_response.text)
    creation_date = re.findall('"created":"(.*?)"', form_response.text)
    is_preview = re.findall('"isPreview":(.*?)}', form_response.text)
    primary_id = [] #Empty list to hold newly created primary ids.
    alma_response_list = [] #Empty list to hold response received from Alma API or when the form is a preview.

    #Create dictionary to match selected home library with Alma campus codes, store new users campus code in campus varibale.
    replacement_dict = {'Blacktown': '0510', 'North Sydney': '0520', 'Strathfield': '0530', 'Brisbane': '0540',
                        'Canberra': '0560', 'Ballarat': '0580', 'Melbourne': '0580'}
    campus = [replacement_dict[element] if element in replacement_dict else element for element in library]

    current_date = datetime.now() #find current date to create expiry and purge dates

    #Loop used to iterate over each new user form and send relevant data to Alma to create a new user.
    for i in range(len(form_instance_id)):
        primary_id.append('AC'+  campus[i] + form_instance_id[i]) #Create primary ID from campus ID and from instance ID.

        #If the form is a preview stop processing, add to response list that a record was not created in Alma.
        if is_preview[i] == 'true':
            alma_response_list.append('Form instance ' + form_instance_id[i]+ 
                                      ' is a preview only. User record has not be created in Alma.')

        #If the form is not a preview proceed to create JSON data and create user in Alma.
        else:
            
            #Create barcode for each user
            barcode_end = str(random.randint(10000000,99999999))
            barcode_leader = '49339'
            barcode = barcode_leader + barcode_end
            
            #Create password for each user, using their last name and phone number and remove any potential spaces.
            password = first_name[i].replace(" ", "") + phone[i].replace(" ", "")

            #If the new user's group is a Reciprocal/ULANZ.
            if user_group[i] == 'Reciprocal institution':
                #Set expiry to 1 years (plus a couple of days to account for leap years and any other delays).
                expiry = current_date + timedelta(days=368)
                expiry_date = expiry.strftime("%Y-%m-%d") #Convert expiry to string only including the date, not time.
                #Set purge to 1.5 years (plus a couple of days to account for leap years and any other delays).
                purge = current_date + timedelta(days=551)
                purge_date = purge.strftime("%Y-%m-%d") #Convert purge to string only including the date, not time.
                statistic_category = reciprocal_institution[i] #Set the entered reciprocal instiution as the statsic category.
                category_type = 'ULANZ' #Set catergory_type as ULANZ.

            #If the new user's group is not Reciprocal (is Community or Alumni).
            else:
                #Set expiry to 5 years (plus a couple of days to account for leap years and any other delays).
                expiry = current_date + timedelta(days=1828)
                expiry_date = expiry.strftime("%Y-%m-%d") #Convert expiry to string only including the date, not time.
                #Set purge to 5.5 years (plus a couple of days to account for leap years and any other delays).
                purge = current_date + timedelta(days=2011)
                purge_date = expiry.strftime("%Y-%m-%d") #Convert purge to string only including the date, not time.
                statistic_category = user_group[i] #Set the selected user group as the statsic category.
                category_type = 'Other NonACU' #Set catergory_type as Other NonACU.

            #Data object to be sent as POST request to Alma, contains user details in JSON.
            json_data = '''
            {
              "link": "",
              "record_type": {
                "value": "PUBLIC"
              },
              "primary_id": "'''+  primary_id[i] +'''",
              "first_name": "'''+ first_name[i] +'''",
              "last_name": "'''+ surname[i] +'''",
              "user_group": {
                "value": "80"
              },
              "campus_code": {
                "value": "'''+ campus[i] +'''"
              },
              "expiry_date": "'''+ expiry_date +'''",
              "purge_date": "'''+ purge_date +'''",
              "account_type": {
                "value": "INTERNAL"
              },
              "external_id": "",
              "password": "''' + password + '''",
              "force_password_change": "TRUE",
              "status": {
                "value": "INACTIVE"
              },
              "contact_info": {
                "address": [
                  {
                    "preferred": "true",
                    "segment_type": "Internal",
                    "line1": "'''+ address[i] +'''",
                    "city": "'''+ suburb[i] +'''",
                    "state_province": "'''+ state[i] +'''",
                    "postal_code": "'''+ postcode[i] +'''",
                    "country": {
                      "value": "AUS"
                    },
                    "address_type": [
                      {
                        "value": "home"
                      }
                    ]
                  }
                ],
                "email": [
                  {
                    "preferred": "true",
                    "segment_type": "Internal",
                    "email_address": "'''+ email[i] +'''",
                    "description": "",
                    "email_type": [
                      {
                        "value": "personal"
                      }
                    ]
                  }
                ],
                "phone": [
                  {
                    "preferred": "true",
                    "preferred_sms": "false",
                    "segment_type": "Internal",
                    "phone_number": "'''+ phone[i] +'''",
                    "phone_type": [
                      {
                        "value": "home"
                      }
                    ]
                  }
                ]
              },
              "user_identifier": [
              {
              "segment_type": "Internal",
              "id_type": {
              "value": "01"
              },
              "value": "'''+ barcode +'''",
              "status": "ACTIVE"
              }
              ],
              "user_note": [
              {
              "segment_type": "External",
              "note_type": {
              "value": "REGISTAR"
              },
              "note_text": "Registration form submitted '''+ creation_date[i] +''' EST. ACU Library privacy statement version '''+ privacy_version[i] + '''.",
              "user_viewable": false,
              "popup_note": false
              }
              ],
              "user_statistic": [
                {
                  "segment_type": "External",
                  "statistic_category": {
                    "value": "'''+ statistic_category +'''"
                  },
                  "category_type": {
                    "value": "'''+ category_type +'''"
                  },
                  "statistic_owner": "",
                  "statistic_note": ""
                }
              ]
            }
            '''

            #Send request using alma POST URL and data object to Alma. Reponse will be contained in the variable.
            alma_response = req.post(alma_url, headers=alma_headers, data=json_data.encode('utf-8'))

            #Selection statement if there is an error add error message to alma_response_list, else No errors detected.
            #Testing for API url error, if error pressent add error to notes column.
            if alma_url_error in alma_response.text:
                note = re.search(alma_error_message, alma_response.text)
                alma_response_list.append(note.group(1))
                print('Primary ID: ' + primary_id[i] + ' error detected when trying to create account in Alma.')
                print('')

            #Testing for data object error, if error pressent add error to alma_response_list.
            elif alma_data_object_error in alma_response.text:
                note = alma_response.text
                alma_response_list.append(note)
                print('Primary ID: ' + primary_id[i] + ' error detected when trying to create account in Alma.')
                print('')

            #Else no errors, add "No errors detected" to alma_response_list.    
            else:
                note = 'No errors detected'
                alma_response_list.append(note)
                
                #If no error print out information to send to AskACU.
                print('User successfully created in Alma, send the following details to AskACU.')
                print('Campus: ' + library[i])
                print('Surname: ' + surname[i])
                print('First name: ' + first_name[i])
                print('Barcode: ' + barcode)
                print('Primary ID: ' + primary_id[i])
                print('Expiry date: ' + expiry_date)
                print('email: ' + email[i])
                print('Phone: ' + phone[i])
                print('User group: ' + user_group[i])
                print('')
                
    #Create dataframe to store output data.
    df_data = {'Libwizard form instance' : form_instance_id, 'Primary ID' : primary_id , 'Surname' : surname, 
               'First name' : first_name,'Home library' : library, 'User group' : user_group, 
               'Reciprocal institution' : reciprocal_institution, 'Is preview' : is_preview,
               'Alma API response' : alma_response_list}
    df = pd.DataFrame(df_data, columns=['Libwizard form instance', 'Primary ID' , 'Surname','First name', 'Home library', 
                                        'User group', 'Reciprocal institution', 'Is preview', 'Alma API response'] )

    #save data frame to csv file.
    df.to_csv('borrower_registration_alma_response.csv')

    #Print information on number of records and the file name they have been saved to.
    print(str(i + 1) + 
          ' records processed and added to borrower_registration_alma_response.csv file, please check file for further details.')
