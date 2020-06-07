class CustomMiddleWares(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        error_message = request.session.pop("error_message", None)
        request.error_message = error_message
        return self.get_response(request)