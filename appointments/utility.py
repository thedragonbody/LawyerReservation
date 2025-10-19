import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar.events']
SERVICE_ACCOUNT_FILE = 'path/to/service_account.json'  # مسیر فایل JSON

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)

service = build('calendar', 'v3', credentials=credentials)

def create_google_meet_event(summary, start_time, end_time, attendees_emails):
    """
    ایجاد Event با لینک Google Meet
    """
    event = {
        'summary': summary,
        'start': {'dateTime': start_time.isoformat(), 'timeZone': 'Asia/Tehran'},
        'end': {'dateTime': end_time.isoformat(), 'timeZone': 'Asia/Tehran'},
        'attendees': [{'email': email} for email in attendees_emails],
        'conferenceData': {'createRequest': {'requestId': f'{summary}-{start_time.timestamp()}', 'conferenceSolutionKey': {'type': 'hangoutsMeet'}}}
    }

    created_event = service.events().insert(
        calendarId='primary',
        body=event,
        conferenceDataVersion=1
    ).execute()

    meet_link = created_event.get('hangoutLink')
    return meet_link