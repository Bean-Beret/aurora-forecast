import pandas as pd
import re
from io import StringIO
import datetime
from urllib.request import urlopen
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content

# the NOAA website we'll get the aurora forecast from:
link = "https://services.swpc.noaa.gov/text/3-day-forecast.txt"
# Open the webpage and grab the text on the page (the forecast)
f = urlopen(link)
myfile = f.read()
text = myfile.decode('utf-8')

# Grab the subset of the text on the page that's the table with the forecast over the next 3 days:
current_year = datetime.date.today().year
first_string_subset = text.split("NOAA Kp index breakdown", 1)[1]
second_string_subset = first_string_subset.split(str(current_year), 1)[1]
third_string_subset = second_string_subset.split("Rationale", 1)[0]

# remove parentheses & brackets and the text between those parentheses & brackets:
clean_table = re.sub("[\(\[].*?[\)\]]", "", third_string_subset)

# turn that text table into a pandas dataframe:
STRINGDATA = StringIO(clean_table)
raw_data = pd.read_csv(STRINGDATA, sep="\n|\s+", header=None)

# drop the first row:
df = raw_data.iloc[1:]
# drop some columns that are all "NA"
df = df.dropna(axis=1, how='all')

# the next few lines deal with the data table headers, which are the dates of the next 3 days, in the format like this:
# Aug 9      Aug 10      Aug 11
# Replace all the instances of a string of spaces witha single space; remove leading and trailing space
headers = re.sub("\s+", " ", raw_data.iloc[0].to_string(index=False)).strip()
# create a list that has each date. This is done using a regex phrase that looks for 3 letters followed by a space, then 1 or 2 digits:
col_names = re.findall("[A-Za-z][A-Za-z][A-Za-z]\s\d{1,2}", headers)
# add "time" to the front of the list. The first variable/column in the table is the time of the day/night
col_names.insert(0, 'time')
# add our cleaned up column names to the dataframe with the Kp values
df.columns = col_names

# convert the data table from wide to long format
df = pd.melt(df, id_vars='time', value_vars=col_names[1:])
df['value'] = pd.to_numeric(df['value'])
# rank the Kp values, then order the data table so the biggest values are at the top of the table:
df['rank'] = df['value'].rank(method='first', ascending=False)
df = df.sort_values(by=['rank'])
df = df[0:5]

# find the max Kp value over the next 3 days:
max_value = df['value'].max()


# If the forecast Kp index will be equal to or above 5 at any point in the next 3 days, send an email alert using the "SendGrid" service:
if (max_value >= 5):
    sg = sendgrid.SendGridAPIClient(api_key='INPUT YOUR SENDGRID API KEY HERE')
    from_email = Email('YOUR SENDER EMAIL GOES HERE')  # Change to your verified sender
    to_email = To('THE EMAIL OF THE PERSON WHO WILL GET THE EMAIL GOES HERE')  # Change to your recipient
    subject = "Aurora forecast"
    content = Content("text/plain", "\nAt " +
                    str(df.iloc[0]['time']) + ' on ' + str(df.iloc[0]['variable']) +
                    ' the Kp index is forecast to be ' + str(df.iloc[0]['value']) + '!' +
                    '\n\n\nFor more details, visit:\n\n' + 'https://services.swpc.noaa.gov/text/3-day-forecast.txt')
    mail = Mail(from_email, to_email, subject, content)
    # Get a JSON-ready representation of the Mail object
    mail_json = mail.get()
    # Send an HTTP POST request to /mail/send
    response = sg.client.mail.send.post(request_body=mail_json)
    #print(response.status_code)
    #print(response.headers)

