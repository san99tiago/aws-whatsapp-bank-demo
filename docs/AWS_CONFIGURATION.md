# AWS-CONFIGURATION

1. Configure the AWS Secret with the Meta Tokens and Secrets.

These are the values to be replaced in the following steps:

- `REPLACE_ME_ENVIRONMENT` --> Replace with `dev` or `prod` based on the target env.
- `REPLACE_ME_SECRET`: Replace with the USER-DEFINED token for WebHook to API. This can be anything.
- `REPLACE_ME_META_TOKEN` --> Replace with the secret API Token from Meta App (from the Meta for Developers Platform).
- `REPLACE_ME_PHONE_NUMBER_ID` --> Replace with the Phone Number ID from Meta for Developers Platform. (API Setup Section).

You can use the next AWS CLI command by replacing the values with the real ones:

```bash
aws secretsmanager create-secret \
    --name "/{REPLACE_ME_ENVIRONMENT}/aws-whatsapp-bank-demo" \
    --secret-string '{"AWS_API_KEY_TOKEN":"{REPLACE_ME_SECRET}","META_TOKEN":"{REPLACE_ME_META_TOKEN}","META_FROM_PHONE_NUMBER_ID":"{REPLACE_ME_PHONE_NUMBER_ID}"}' \
    --description 'META Tokens for my AWS WhatsApp Chatbot demos for RUFUS bank'
```
