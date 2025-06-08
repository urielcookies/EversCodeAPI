from apps.EversPass import everspass_bp

@everspass_bp.route('/create-session', methods=['POST'])
def createSession():
    return "Hello from EversPass!"