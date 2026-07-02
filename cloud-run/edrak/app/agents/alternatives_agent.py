from app.agents.tools import safer_options_tool


def generate_alternatives(profile, decision_input, metrics):
    return safer_options_tool(profile, decision_input, metrics)
