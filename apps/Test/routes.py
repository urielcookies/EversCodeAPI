from apps.Test import test_bp

@test_bp.route('/')
def index():
    return "Hello from Test app!"