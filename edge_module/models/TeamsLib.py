import json
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
_logger = logging.getLogger(__name__)

class TeamsLib:
    def __init__(self):
        # App registration details
        self.client_id = "5a2f2fe4-8779-471f-a14f-809a9e25abad"
        self.client_secret = "bsp8Q~tn35EAAizZ42LvHfsewb_5WViWT83eEcQW"
        self.tenant_id = "1876f61a-3bdb-4843-ae70-75ed0ccb7404"
        self.authority = f'https://login.microsoftonline.com/{self.tenant_id}'
        self.scope = ['https://graph.microsoft.com/.default']
        
        # Service account credentials
        self.username = "YodelayHeedoo@edgeautonomy.io"
        self.password = "Uncharted-Stride-Untie8-Umbilical"
        
        _logger.info(f"TeamsLib initialized with tenant_id: {self.tenant_id}")

    def authenticate(self):
        """Authenticate with application permissions"""
        try:
            _logger.debug("Attempting to authenticate with Microsoft Graph API (app permissions)")
            
            token_url = f'https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token'
            
            data = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': 'https://graph.microsoft.com/.default'
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            response = requests.post(token_url, data=data, headers=headers)
            
            if response.status_code == 200:
                token_data = response.json()
                _logger.info("Successfully acquired access token")
                return token_data.get('access_token')
            else:
                _logger.error(f"Failed to acquire token. Status code: {response.status_code}, Response: {response.text}")
                return None
                
        except Exception as e:
            _logger.error(f"Authentication failed with exception: {str(e)}", exc_info=True)
            raise

    def authenticate_delegated(self):
        """Authenticate with delegated permissions using password grant flow"""
        try:
            _logger.debug("Attempting to authenticate with delegated permissions")
            
            token_url = f'https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token'
            
            data = {
                'grant_type': 'password',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': 'https://graph.microsoft.com/.default',
                'username': self.username,
                'password': self.password
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            response = requests.post(token_url, data=data, headers=headers)
            
            if response.status_code == 200:
                token_data = response.json()
                _logger.info("Successfully acquired delegated access token")
                return token_data.get('access_token')
            else:
                _logger.error(f"Failed to acquire delegated token. Status code: {response.status_code}, Response: {response.text}")
                return None
                
        except Exception as e:
            _logger.error(f"Delegated authentication failed with exception: {str(e)}", exc_info=True)
            raise

    def get_user_id(self, email):
        """Get the user ID for a given email address"""
        try:
            _logger.info(f"Attempting to get user ID for email: {email}")
            access_token = self.authenticate()
            if not access_token:
                _logger.error("Cannot get user ID - authentication failed")
                return None

            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json'
            }
            users_endpoint = f"https://graph.microsoft.com/v1.0/users/{email}"
            
            _logger.debug(f"Sending GET request to {users_endpoint}")
            user_response = requests.get(users_endpoint, headers=headers)
            
            if user_response.status_code == 200:
                user_data = user_response.json()
                user_id = user_data.get('id')
                _logger.info(f"Successfully retrieved user ID: {user_id}")
                return user_id
            else:
                _logger.error(f"Failed to get user ID. Status code: {user_response.status_code}, Response: {user_response.text}")
                return None

        except Exception as e:
            _logger.error(f"Error getting user ID: {str(e)}", exc_info=True)
            return None

    def create_or_get_chat(self, recipient_email):
        """Create a new chat or get an existing chat with a user"""
        try:
            _logger.info(f"Creating or getting chat with recipient: {recipient_email}")
            
            # Get user IDs
            recipient_id = self.get_user_id(recipient_email)
            if not recipient_id:
                _logger.error(f"Could not find recipient ID for {recipient_email}")
                return None
                
            sender_id = self.get_user_id(self.username)
            if not sender_id:
                _logger.error(f"Could not find sender ID for {self.username}")
                return None
            
            # Get application token for creating chat
            app_token = self.authenticate()
            if not app_token:
                _logger.error("Cannot create chat - authentication failed")
                return None

            # First try to list existing chats to see if we already have one with this user
            headers = {
                'Authorization': f'Bearer {app_token}',
                'Content-Type': 'application/json'
            }
            
            # Try to create a new chat between the users
            member1 = {
                "@odata.type": "#microsoft.graph.aadUserConversationMember",
                "roles": ["owner"],
                "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{sender_id}')"
            }

            member2 = {
                "@odata.type": "#microsoft.graph.aadUserConversationMember",
                "roles": ["owner"],
                "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{recipient_id}')"
            }

            chat_payload = {
                "chatType": "oneOnOne",
                "members": [member1, member2]
            }
            
            _logger.debug(f"Creating chat with payload: {json.dumps(chat_payload)}")
            chat_response = requests.post(
                'https://graph.microsoft.com/v1.0/chats',
                headers=headers,
                json=chat_payload
            )
            
            # Check response and extract chat ID
            if chat_response.status_code in [201, 200]:
                chat_data = chat_response.json()
                chat_id = chat_data.get('id')
                _logger.info(f"Successfully created/found chat with ID: {chat_id}")
                return chat_id
            else:
                _logger.error(f"Failed to create chat. Status: {chat_response.status_code}, Response: {chat_response.text}")
                
                # If we couldn't create a new chat, it might already exist
                # For brevity we're simplifying this process, in a production environment
                # you would implement proper error handling and chat lookup here
                
                return None

        except Exception as e:
            _logger.error(f"Error creating/getting chat: {str(e)}", exc_info=True)
            return None

    def send_message(self, recipient_email, message, title=None, link_url=None, link_text=None):
        """Send a message to a user in Teams"""
        try:
            _logger.info(f"Attempting to send message to recipient: {recipient_email}")
            
            # Format the message with title if provided
            content = message
            if title:
                # Add HTML line breaks for proper formatting in Teams
                content = f"<strong>{title}</strong><br>{message}"
                
            # Add button/link if provided
            if link_url and link_text:
                # Create a button-like appearance using HTML
                button_html = f'<br><br><a href="{link_url}" style="padding: 8px 16px; background-color: #6264A7; color: white; text-decoration: none; border-radius: 4px; display: inline-block; font-weight: bold;">{link_text}</a>'
                content += button_html
            
            # Get or create a chat with the recipient
            chat_id = self.create_or_get_chat(recipient_email)
            if not chat_id:
                _logger.error("Failed to get chat ID, cannot send message")
                return False
            
            # First try with delegated permissions
            delegated_token = self.authenticate_delegated()
            if delegated_token:
                _logger.info("Using delegated token for sending message")
                auth_token = delegated_token
            else:
                # Fall back to application permissions if delegated auth fails
                _logger.warning("Delegated authentication failed, falling back to application permissions")
                auth_token = self.authenticate()
                if not auth_token:
                    _logger.error("All authentication methods failed, cannot send message")
                    return False

            # Send the message
            url = f"https://graph.microsoft.com/v1.0/chats/{chat_id}/messages"
            body = {
                "body": {
                    "content": content,
                    "contentType": "html"
                }
            }
            
            headers = {
                'Authorization': f'Bearer {auth_token}',
                'Content-Type': 'application/json'
            }

            _logger.debug(f"Sending message to chat: {chat_id}")
            response = requests.post(url, json=body, headers=headers)
            
            if response.status_code in [200, 201]:
                _logger.info("Message sent successfully")
                return True
            else:
                _logger.error(f"Failed to send message. Status code: {response.status_code}, Response: {response.text}")
                
                # If using application permissions and getting a permission error,
                # inform the user about the required permissions
                if auth_token != delegated_token and "AccessDenied" in response.text:
                    _logger.error("Application needs Chat.ReadWrite.All permission to send messages")
                
                return False

        except Exception as e:
            _logger.error(f"Error sending message: {str(e)}", exc_info=True)
            return False

    def send_message_to_webhook(self, webhook_url, message, title="Notification"):
        """Send a message to a Teams channel using a webhook"""
        try:
            _logger.info(f"Sending message to Teams webhook with title: {title}")
            headers = {
                "Content-Type": "application/json"
            }
            content = {
                "@context": "https://schema.org/extensions",
                "@type": "MessageCard",
                "title": title,
                "text": message
            }
            
            response = requests.post(
                webhook_url, 
                headers=headers, 
                json=content
            )
            
            if response.status_code == 200:
                _logger.info("Successfully sent message to Teams webhook")
                return True
            else:
                _logger.error(f"Failed to send message to webhook. Status code: {response.status_code}, Response: {response.text}")
                return False

        except Exception as e:
            _logger.error(f"Error sending message to webhook: {str(e)}", exc_info=True)
            return False
        
    # Test function
if __name__ == "__main__":
    # Create test message
    import datetime
    request_id = 12
    request_name = "PR00012"
    
    # Create the base URL (you might need to set this in Odoo system parameters)
    base_url = "https://edgehsv-staging0228-18720734.dev.odoo.com"
    
    # Create the link to the purchase request
    link_url = f"{base_url}/web#id={request_id}&model=purchase.request&view_type=form"
    link_text = "View Purchase Request"
    
    title = "Purchase Request Approval Needed"
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    test_recipient = "bmccoy@edgeautonomy.io"
    test_message = f"Hi Bailee. Just testing if this works. Can you text me if this gets to you? Thanks!"
    test_title = "Teams Integration Test"
    
    print(f"Sending test message to {test_recipient}...")
    
    # Initialize Teams library and send test message
    teams = TeamsLib()
    success = teams.send_message(test_recipient, test_message, title, link_url, link_text)
    
    if success:
        print("✅ Test message sent successfully!")