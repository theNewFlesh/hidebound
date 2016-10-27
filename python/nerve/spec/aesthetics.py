#! /usr/bin/env python
'''
The base module houses all the base specifications for nerve entities

Those entities include: configs, projects, deliverables and deliverables.

All specifications used in production should be subclassed from the
aforementioned classes.  All class attributes must have a "get_[attribute]"
function in the traits module and should have one or more validators related t
the value of that trait (especially if required).
'''
# ------------------------------------------------------------------------------

import re
import yaml
from schematics.models import Model, BaseType
from schematics.types import StringType, IntType, BooleanType, FloatType
from schematics.types.compound import ListType, DictType, ModelType
from schematics.exceptions import ValidationError
# ------------------------------------------------------------------------------

class Color(BaseType):
    def validate_color(self, data):
        messages = []
        if data.__class__.__name__ in ['list', 'tuple']:
            cols = ['hue', 'saturation', 'value']
            for chan, item in zip(cols, data):
                if item.__class__.__name__ not in ['int', 'float']:
                    messages.append(chan + ' is not an int or float')

        elif isinstance(data, str):
            found = re.search('#[A-F0-9]{6}', data)
            if not found:
                messages.append(data + ' is not a valid hex')

        else:
            messages.append(type(data) + ' is not a valid type')

        if len(messages) > 0:
            raise ValidationError('\n'.join(messages))

class Palette(Model):
    def __getitem__(self, key):
        if isinstance(key, int):
            key = 'l' + str(key)
        return getattr(self, key)

    def items(self):
        output = filter(lambda x: x[1] != None, super().items())
        return list(output)

    l0 = ListType(Color)
    l1 = ListType(Color)
    l2 = ListType(Color)
    l3 = ListType(Color)
    l4 = ListType(Color)
    l5 = ListType(Color)
    l6 = ListType(Color)
    l7 = ListType(Color)
    l8 = ListType(Color)
    l9 = ListType(Color)
    l10 = ListType(Color)
    l11 = ListType(Color)
    l12 = ListType(Color)
    l13 = ListType(Color)
    l14 = ListType(Color)
    l15 = ListType(Color)
    l16 = ListType(Color)
    l17 = ListType(Color)
    l18 = ListType(Color)
    l19 = ListType(Color)
    l20 = ListType(Color)
    l21 = ListType(Color)
    l22 = ListType(Color)
    l23 = ListType(Color)



class Lighting(Model):
    ambient   = FloatType(required=True)
    diffuse   = FloatType(required=True)
    fresnel   = FloatType(required=True)
    roughness = FloatType(required=True)
    specular  = FloatType(required=True)

class AppearanceElement(Model):
    def __init__(self, raw_data={}, **kwargs):
        data = raw_data
        if data != {}:
            hues = data['hues']
            saturations = data['saturations']
            value = data['value']

            palette = {}
            for i, hue in enumerate(data['hues']):
                palette['l' + str(i)] = list(
                    product([hue], saturations, [value])
                )
            if 'palette' in data.keys():
                for l, items in data['palette'].items():
                    for i, item in enumerate(items):
                        palette[l][i] = item
            data['palette'] = palette

        super().__init__(raw_data=data, **kwargs)

    value       = FloatType(required=True)
    hues        = ListType(FloatType, required=True)
    saturations = ListType(FloatType, required=True)
    texture     = BaseType()
    material    = BaseType()
    lighting    = ModelType(Lighting)
    palette     = ModelType(Palette, required=True)
# ------------------------------------------------------------------------------

class Appearance(Model):
    overlay = ModelType(AppearanceElement)
    figure  = ModelType(AppearanceElement)
    ground  = ModelType(AppearanceElement)

class Element(Model):
    appearance = ModelType(AppearanceElement)

class Overlay(Element):
    pass

class Figure(Element):
    pass

class Ground(Element):
    pass
# ------------------------------------------------------------------------------

def main():
    '''
    Run help if called directly
    '''

    import __main__
    help(__main__)
# ------------------------------------------------------------------------------

# __all__ = [
#     'Appearance',
#     'Overlay',
#     'Figure',
#     'Ground'
# ]

if __name__ == '__main__':
    main()
