from gorilaml.plugins import plugin, output
from gorilaml.lab import authorize

gorilaml = plugin('helloworld', __name__, url_prefix='/helloworld', template_folder='templates', static_folder='static')

@gorilaml.route('/')
@authorize
def index():
    return output('doc.html')