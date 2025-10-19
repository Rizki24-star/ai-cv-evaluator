from models import APIResponse

def create_response(success: bool, message: str, data=None, error=None):
    response = {"success": success, "message": message}
    if data is not None:
        response["data"] = data
    if error is not None:
        response["error"] = error
    return response
