class OrchestrationController:
    def __init__(self, allowlist):
        self.allowlist = allowlist

    def coordinate_tool_integration(self, tool_name, params):
        if self._is_tool_allowed(tool_name):
            try:
                # Placeholder for actual tool integration logic
                print(f"Integrating with {tool_name} with parameters: {params}")
            except Exception as e:
                self._handle_error(e)
        else:
            print(f"Tool {tool_name} is not allowed.")

    def _is_tool_allowed(self, tool_name):
        return tool_name in self.allowlist

    def _handle_error(self, error):
        print(f"An error occurred: {str(error)}")

# Example usage
if __name__ == '__main__':
    tool_allowlist = ['tool1', 'tool2', 'tool3']
    controller = OrchestrationController(tool_allowlist)
    controller.coordinate_tool_integration('tool1', {'param1': 'value1'})
    controller.coordinate_tool_integration('tool4', {'param1': 'value4'})