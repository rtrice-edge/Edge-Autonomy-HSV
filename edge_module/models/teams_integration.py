import requests
import json

def send_teams_message(webhook_url, message, title=None):
    """
    Send a message to a Microsoft Teams channel using webhook
    
    Args:
        webhook_url (str): The webhook URL for your Teams channel
        message (str): The message to send
        title (str, optional): Title for the message card
    
    Returns:
        bool: True if successful, False otherwise
    """
    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "text": message
    }
    
    if title:
        payload["title"] = title
    
    try:
        response = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'}
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending message: {e}")
        return False
