#!/bin/bash

# NOTES FOR DEPLOYMENT!!!!

# DEPLOY CHATBOT PROCESSING STACK
cdk deploy rufus-bank-chatbot-api-prod --require-approval never

# DEPLOY GEN-AI MESSAGE PROCESSING STACK
cdk deploy rufus-bank-generative-ai-prod --require-approval never
