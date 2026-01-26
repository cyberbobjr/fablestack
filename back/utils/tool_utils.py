from typing import Any, Callable, Dict, List


def get_cleaned_tool_definitions(tools: List[Callable]) -> List[Dict[str, Any]]:
    """
    Generates OpenAI-compatible tool definitions, stripping the 'ctx' argument
    that PydanticAI tools expect.
    """
    definitions = []
    # We can use LangChain's utils or pydantic to generate schema, 
    # but simplest is to use langchain_core.utils.function_calling.convert_to_openai_tool
    # and then manually remove 'ctx' from properties.
    from langchain_core.utils.function_calling import convert_to_openai_tool
    
    for tool in tools:
        schema = convert_to_openai_tool(tool)
        # Check parameters
        if "function" in schema and "parameters" in schema["function"]:
            params = schema["function"]["parameters"]
            if "properties" in params and "ctx" in params["properties"]:
                del params["properties"]["ctx"]
            if "required" in params and "ctx" in params["required"]:
                params["required"].remove("ctx")
        definitions.append(schema)
    return definitions
