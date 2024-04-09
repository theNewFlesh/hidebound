'''
A local database framework for defining and validating assets.

Author: Alex Braun
Email: Alexander.G.Braun@gmail.com
Github: https://github.com/theNewFlesh
'''
import dask
dask.config.set({'dataframe.query-planning-warning': False})

import hidebound.command  # noqa F401
import hidebound.core  # noqa F401
import hidebound.exporters  # noqa F401
import hidebound.server  # noqa F401
