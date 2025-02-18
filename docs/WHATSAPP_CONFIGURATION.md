# WHATSAPP CONFIGURATION

In order to correctly configure the Meta Developer settings and projects (only once), follow these steps.

## Manual Steps (Configure WhatsApp "Free Tier" Business/API)

1. Create "Meta for Developers" account:

   - https://business.facebook.com
   - https://youtu.be/CEt_KMMv3V8?list=PLX_K_BlBdZKi4GOFmJ9_67og7pMzm2vXH
   - https://youtu.be/VDlyGcHlGiw

2. Create an App:

   - Select "Type" == "Business"
   - App Name == "ADD_NAME" (eg "san99tiagodemos")
   - Contact == "ADD_EMAIL" (eg "san99tiago+metademos@gmail.com")

3. Enable the "WhatsApp Integration":

   - Click on "Integrate with WhatsApp"

4. Create a "Business portfolio in Business Manager"

   - Business Name == "ADD_NAME" (eg "SANTI")
   - Person's Name == "ADD_NAME" (eg "Santiago Garcia Arango")
   - Business Email == "ADD_EMAIL" (eg "san99tiago+metademos@gmail.com")

5. Configure the "WhatsApp Business API"

   - On the "WhatsApp Business Platform API", select the business portfolio created on "step 4"
   - Accept terms and conditions and we should be ready to send messages to up to 5 numbers in the free tier!
   - We will use the given "test number" for now (as we don't want to add a custom number for this PoC)
   - We can register up to 5 free "recipients" phone numbers in the free tier (eg "our real phone number")

6. As soon as the CDK deployment on AWS finishes, we should be able to provide the "WebHook Endpoint" to the WhatsApp Webhook's "Callback URL":

   - Important: there will be a "Verify Token" that needs to be provided from the service
   - Then, we can configure the desired incoming events via the "Webhook fields" option on the configuration (eg "messages")

7. Create Business System User. Inside the "App Settings", go to on "Basic", then click on the business name (eg. "SANTI")

   - Inside the "Meta Business Suite", go to "System Users"
   - Click on "Add"
   - "system user name" == "ADD_NAME" (eg. "admin_santi")
   - "system user role" == "Admin"

8. Configure the Admin User. Click on the created user.

   - Select "Assign Assets"
   - Select "Apps"
   - Select the name of the app (the one created on "step 2") (eg. "san99tiago")
   - Allow "Full Control" for the app

9. Generate the permanent token. On the system user panel click on "Generate token"
   - Select the name of the app (the one created on "step 2") (eg. "san99tiago")
   - Set expiration (either 60 days or "never")
   - Assign permissions "whatsapp_business_messaging" and "whatsapp_business_management"
   - Click on "Generate token"
   - Store the token in a secret and encrypted place (in my case it was "Secrets Manager" on AWS)
