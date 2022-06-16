import flask_healthz
import flasgger

from hidebound.server.extension import HideboundExtension
# ------------------------------------------------------------------------------

hidebound = HideboundExtension()
swagger = flasgger.Swagger()
healthz = flask_healthz.Healthz()
