# TEST TO INTERACT WITH AGENT LOCALLY

from backend.state_machine.processing.bedrock_agent import call_bedrock_agent


if __name__ == "__main__":
    input_string = "Hola"
    response = call_bedrock_agent(input_string, "LocalTestingSession")
